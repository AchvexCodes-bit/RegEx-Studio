"""Bounded ASCII regular-expression parser and automata algorithms.

Supported: literals, groups, alternation, concatenation, classes, ., common
ASCII shorthand classes, and *, +, ?, {m}, {m,}, {m,n}. Full-string matching.
Unsupported constructs fail loudly. This module has no Django dependency.
"""
from __future__ import annotations
from dataclasses import dataclass
import string

ALPHABET = tuple(chr(i) for i in range(128))
MAX_PATTERN = 512
MAX_REPEAT = 32
MAX_STATES = 1200

class RegexSyntaxError(ValueError):
    def __init__(self, message: str, position: int):
        self.message, self.position = message, position
        super().__init__(f"{message} at position {position}")

@dataclass
class Node:
    kind: str
    value: object = None
    children: tuple["Node", ...] = ()
    start: int = 0
    end: int = 0

class Parser:
    def __init__(self, pattern: str):
        if len(pattern) > MAX_PATTERN: raise RegexSyntaxError("Pattern is too long (limit 512)", MAX_PATTERN)
        self.p, self.i = pattern, 0
    def peek(self): return self.p[self.i] if self.i < len(self.p) else ""
    def take(self):
        c=self.peek()
        if c: self.i += 1
        return c
    def parse(self):
        n=self.alt()
        if self.i != len(self.p):
            if self.peek()==")": raise RegexSyntaxError("Unmatched closing parenthesis", self.i)
            raise RegexSyntaxError("Unexpected token", self.i)
        return n
    def alt(self):
        start=self.i; parts=[self.concat()]
        while self.peek()=="|":
            self.take(); parts.append(self.concat())
        return parts[0] if len(parts)==1 else Node("alt",children=tuple(parts),start=start,end=self.i)
    def concat(self):
        start=self.i; parts=[]
        while self.peek() and self.peek() not in ")|":
            parts.append(self.repeat())
        if not parts: return Node("empty",start=start,end=self.i)
        return parts[0] if len(parts)==1 else Node("concat",children=tuple(parts),start=start,end=self.i)
    def repeat(self):
        atom=self.atom(); c=self.peek()
        if c in ("*","+","?") and c:
            self.take(); bounds={"*":(0,None),"+":(1,None),"?":(0,1)}[c]
            n=Node("repeat",bounds,(atom,),atom.start,self.i)
            if self.peek() in ("*","+","?","{") and self.peek(): raise RegexSyntaxError("Nested quantifiers are not supported",self.i)
            return n
        if c=="{":
            pos=self.i; self.take(); digits=""
            while self.peek().isdigit(): digits+=self.take()
            if not digits: raise RegexSyntaxError("Expected repetition lower bound",pos)
            lo=int(digits); hi=lo
            if self.peek()==",":
                self.take(); digits=""
                while self.peek().isdigit(): digits+=self.take()
                hi=int(digits) if digits else None
            if self.peek()!="}": raise RegexSyntaxError("Unclosed or malformed repetition",pos)
            self.take()
            if lo>MAX_REPEAT or (hi is not None and hi>MAX_REPEAT): raise RegexSyntaxError("Repetition limit is 32",pos)
            if hi is not None and hi<lo: raise RegexSyntaxError("Repetition upper bound is smaller than lower bound",pos)
            return Node("repeat",(lo,hi),(atom,),atom.start,self.i)
        return atom
    def atom(self):
        start=self.i; c=self.take()
        if not c: return Node("empty",start=start,end=start)
        if c=="(": 
            n=self.alt()
            if self.peek()!=")": raise RegexSyntaxError("Unclosed group",start)
            self.take(); n.start=start; n.end=self.i; return n
        if c=="[":
            negate=False
            if self.peek()=="^": self.take(); negate=True
            chars=set(); first=True
            while self.peek() and (self.peek()!="]" or first):
                first=False; a=self.class_char(start)
                if self.peek()=="-" and self.i+1<len(self.p) and self.p[self.i+1]!="]":
                    self.take(); b=self.class_char(start)
                    if ord(a)>ord(b): raise RegexSyntaxError("Reversed character range",self.i)
                    chars.update(chr(x) for x in range(ord(a),ord(b)+1) if x<128)
                else: chars.add(a)
            if self.peek()!="]": raise RegexSyntaxError("Unclosed character class",start)
            self.take()
            if negate: chars=set(ALPHABET)-chars
            return Node("set",frozenset(chars),start=start,end=self.i)
        if c=="\\":
            if not self.peek(): raise RegexSyntaxError("Trailing escape",start)
            e=self.take()
            sets={"d":set(string.digits),"w":set(string.ascii_letters+string.digits+"_"),"s":set(" \t\r\n\f\v")}
            if e.lower() in sets:
                chars=sets[e.lower()]
                if e.isupper(): chars=set(ALPHABET)-chars
                return Node("set",frozenset(chars),start=start,end=self.i)
            literals={"n":"\n","r":"\r","t":"\t","f":"\f","v":"\v"}
            if e.isalpha() and e not in literals: raise RegexSyntaxError(f"Unsupported escape \\{e}",start)
            return Node("lit",literals.get(e,e),start=start,end=self.i)
        if c==".": return Node("set",frozenset(set(ALPHABET)-{"\n","\r"}),start=start,end=self.i)
        if c in "^$)": raise RegexSyntaxError(f"Unsupported or unexpected token {c!r}",start)
        if c in "*+?{}": raise RegexSyntaxError("Quantifier has no preceding atom",start)
        return Node("lit",c,start=start,end=self.i)
    def class_char(self,start):
        c=self.take()
        if c=="\\":
            if not self.peek(): raise RegexSyntaxError("Trailing escape in character class",start)
            e=self.take()
            m={"n":"\n","r":"\r","t":"\t"}
            if e.lower() in ("d","w","s"): raise RegexSyntaxError("Shorthand classes inside ranges are not supported yet",self.i-2)
            return m.get(e,e)
        return c

class NFA:
    def __init__(self): self.transitions={}; self.start=0; self.accept=0; self.next_id=0
    def state(self):
        if self.next_id>=MAX_STATES: raise RegexSyntaxError("Automaton state limit exceeded",0)
        s=self.next_id; self.next_id+=1; self.transitions[s]=[]; return s
    def edge(self,a,b,label=None): self.transitions[a].append((label,b))
    def build(self,n):
        if n.kind=="empty":
            a=self.state(); b=self.state(); self.edge(a,b); return a,b
        if n.kind in ("lit","set"):
            a=self.state(); b=self.state(); chars={n.value} if n.kind=="lit" else set(n.value); self.edge(a,b,frozenset(chars)); return a,b
        if n.kind=="concat":
            a,b=self.build(n.children[0])
            for child in n.children[1:]:
                c,d=self.build(child); self.edge(b,c); b=d
            return a,b
        if n.kind=="alt":
            a=self.state(); b=self.state()
            for child in n.children:
                c,d=self.build(child); self.edge(a,c); self.edge(d,b)
            return a,b
        if n.kind=="repeat":
            lo,hi=n.value; child=n.children[0]; pieces=[]
            for _ in range(lo): pieces.append(child)
            a=self.state(); cursor=a
            for item in pieces:
                c,d=self.build(item); self.edge(cursor,c); cursor=d
            if hi is None:
                c,d=self.build(child); end=self.state()
                self.edge(cursor,end); self.edge(cursor,c); self.edge(d,c); self.edge(d,end)
                return a,end
            for _ in range(hi-lo):
                c,d=self.build(child); end=self.state()
                self.edge(cursor,end); self.edge(cursor,c); self.edge(d,end); cursor=end
            if hi==lo:
                end=self.state(); self.edge(cursor,end); return a,end
            return a,cursor
        raise ValueError("Unknown AST node: "+n.kind)
    def compile(self,node):
        self.start,self.accept=self.build(node); return self
    def closure(self,states):
        out=set(states); stack=list(states)
        while stack:
            s=stack.pop()
            for label,t in self.transitions[s]:
                if label is None and t not in out: out.add(t); stack.append(t)
        return frozenset(out)
    def step(self,states,ch):
        dest=set()
        for s in states:
            for label,t in self.transitions[s]:
                if label is not None and ch in label: dest.add(t)
        return self.closure(dest)
    def simulate(self,text):
        if len(text)>4096: raise ValueError("Input limit is 4096 characters")
        states=self.closure({self.start}); trace=[{"index":0,"char":"","active":sorted(states),"epsilon":True}]
        for i,ch in enumerate(text):
            if ord(ch)>=128: states=frozenset()
            else: states=self.step(states,ch)
            trace.append({"index":i+1,"char":ch,"active":sorted(states),"epsilon":False})
        return {"matched":self.accept in states,"trace":trace,"state_count":self.next_id}

def parse(pattern): return Parser(pattern).parse()

def to_dfa(nfa):
    start=nfa.closure({nfa.start}); subsets=[start]; index={start:0}; trans={}
    for subset in subsets:
        sid=index[subset]; trans[sid]={}
        for ch in ALPHABET:
            dest=nfa.step(subset,ch)
            if dest:
                if dest not in index:
                    if len(subsets)>=MAX_STATES: raise ValueError("DFA state limit exceeded")
                    index[dest]=len(subsets); subsets.append(dest)
                trans[sid][ch]=index[dest]
    accepts={index[s] for s in subsets if nfa.accept in s}
    return {"start":0,"transitions":trans,"accepts":accepts,"subsets":subsets}

def minimize_dfa(dfa):
    states=set(dfa["transitions"]); accepts=set(dfa["accepts"]); non=states-accepts
    parts=[p for p in (accepts,non) if p]
    alphabet=ALPHABET
    changed=True
    while changed:
        changed=False; new=[]
        for group in parts:
            buckets={}
            for s in group:
                signature=tuple(next((i for i,p in enumerate(parts) if dfa["transitions"].get(s,{}).get(ch) in p),-1) for ch in alphabet)
                buckets.setdefault(signature,set()).add(s)
            new.extend(buckets.values()); changed |= len(buckets)>1
        parts=new
    mapping={s:i for i,g in enumerate(parts) for s in g}; trans={}
    for i,g in enumerate(parts):
        representative=next(iter(g)); trans[i]={ch:mapping[t] for ch,t in dfa["transitions"].get(representative,{}).items()}
    return {"start":mapping[dfa["start"]],"transitions":trans,"accepts":{mapping[s] for s in accepts},"groups":[sorted(g) for g in parts]}

def compile_pattern(pattern):
    ast=parse(pattern); nfa=NFA().compile(ast); dfa=to_dfa(nfa); minimized=minimize_dfa(dfa)
    return {"ast":ast,"nfa":nfa,"dfa":dfa,"minimized":minimized}

def ast_json(n):
    return {"type":n.kind,"value":sorted(n.value) if n.kind=="set" else n.value,"start":n.start,"end":n.end,"children":[ast_json(c) for c in n.children]}

def graph_json(nfa):
    return {"start":nfa.start,"accept":nfa.accept,"states":[{"id":s,"accept":s==nfa.accept} for s in nfa.transitions],
            "transitions":[{"from":s,"to":t,"label":"ε" if label is None else ("".join(sorted(label)) if len(label)<12 else f"[set:{len(label)}]")} for s,edges in nfa.transitions.items() for label,t in edges]}
