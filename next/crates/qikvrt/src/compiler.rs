// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
use crate::Result;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct SubjectDecl {
    pub name: String,
    pub repository: String,
    pub binding: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RequestDecl {
    pub name: String,
    pub target: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Handler {
    pub event: String,
    pub statements: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Program {
    pub schema: String,
    pub version: String,
    pub authority: String,
    pub subject: SubjectDecl,
    pub request: RequestDecl,
    pub handlers: Vec<Handler>,
    pub dod: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Token {
    Word(String),
    Quoted(String),
    Mark(char),
    And,
}

fn lex(source: &str) -> Result<Vec<Token>> {
    if source.len() > 65536 {
        return Err("SOURCE_TOO_LARGE".into());
    }
    let mut chars = source.char_indices().peekable();
    let mut tokens = Vec::new();
    while let Some((offset, c)) = chars.next() {
        if c.is_ascii_whitespace() {
            continue;
        }
        let token = match c {
            ';' | '{' | '}' | '=' => Token::Mark(c),
            '&' => {
                if chars.next().map(|(_, c)| c) != Some('&') {
                    return Err(format!("EXPECTED_&& at byte {offset}"));
                }
                Token::And
            }
            '"' => {
                let mut s = String::new();
                let mut ended = false;
                for (_, c) in chars.by_ref() {
                    if c == '"' {
                        ended = true;
                        break;
                    }
                    if !(c.is_ascii_alphanumeric() || " /-_.:".contains(c)) {
                        return Err(format!("INVALID_STRING at byte {offset}"));
                    }
                    s.push(c);
                }
                if !ended || s.is_empty() {
                    return Err("UNTERMINATED_OR_EMPTY_STRING".into());
                }
                Token::Quoted(s)
            }
            c if c.is_ascii_alphanumeric() => {
                let mut s = c.to_string();
                while let Some(&(_, n)) = chars.peek() {
                    if n.is_ascii_alphanumeric() || matches!(n, '_' | '-' | '.') {
                        s.push(n);
                        chars.next();
                    } else {
                        break;
                    }
                }
                Token::Word(s)
            }
            _ => return Err(format!("UNEXPECTED_CHARACTER at byte {offset}")),
        };
        tokens.push(token);
    }
    Ok(tokens)
}

struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}
impl Parser {
    fn take(&mut self) -> Result<Token> {
        let t = self.tokens.get(self.pos).cloned().ok_or("UNEXPECTED_END")?;
        self.pos += 1;
        Ok(t)
    }
    fn word(&mut self, w: &str) -> Result<()> {
        if self.take()? == Token::Word(w.into()) {
            Ok(())
        } else {
            Err(format!("EXPECTED_{w} at token {}", self.pos))
        }
    }
    fn mark(&mut self, c: char) -> Result<()> {
        if self.take()? == Token::Mark(c) {
            Ok(())
        } else {
            Err(format!("EXPECTED_{c} at token {}", self.pos))
        }
    }
    fn ident(&mut self) -> Result<String> {
        if let Token::Word(w) = self.take()? {
            if w.as_bytes()[0].is_ascii_alphabetic()
                && w.chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
            {
                return Ok(w);
            }
        }
        Err("IDENTIFIER_REQUIRED".into())
    }
    fn quoted(&mut self) -> Result<String> {
        if let Token::Quoted(w) = self.take()? {
            Ok(w)
        } else {
            Err("QUOTED_STRING_REQUIRED".into())
        }
    }
    fn at_end_block(&self) -> bool {
        self.tokens.get(self.pos) == Some(&Token::Mark('}'))
    }
    fn statement(&mut self) -> Result<String> {
        let op = self.ident()?;
        let s = match op.as_str() {
            "follow" => {
                self.word("exact")?;
                "follow exact".into()
            }
            "classify" => {
                self.word("causal")?;
                "classify causal".into()
            }
            "learn" => {
                self.word("smallest_sound_successor")?;
                "learn smallest_sound_successor".into()
            }
            "execute" => {
                self.word("successor")?;
                "execute successor".into()
            }
            "hold" => {
                let a = self.ident()?;
                self.word("until")?;
                let b = self.ident()?;
                format!("hold {a} until {b}")
            }
            "effect" => {
                let name = self.ident()?;
                self.mark('{')?;
                self.word("require")?;
                self.word("authority")?;
                self.mark(';')?;
                self.word("require")?;
                self.word("validation")?;
                self.mark(';')?;
                self.word("commit")?;
                self.mark(';')?;
                self.word("readback")?;
                self.mark(';')?;
                self.mark('}')?;
                return Ok(format!(
                    "effect {name} {{ require authority; require validation; commit; readback; }}"
                ));
            }
            _ => return Err(format!("UNKNOWN_STATEMENT_{op}")),
        };
        self.mark(';')?;
        Ok(s)
    }
}

/// Full-token parser of the existing v0.1 grammar. No eval, regex extraction,
/// ignored trailing text or execution of source-supplied commands.
pub fn compile(source: &str) -> Result<Program> {
    let mut p = Parser {
        tokens: lex(source)?,
        pos: 0,
    };
    p.word("temdd")?;
    p.word("0.1")?;
    p.mark(';')?;
    let (mut authority, mut subject, mut request, mut dod) = (None, None, None, None);
    let mut handlers = Vec::new();
    let mut handler_kinds = BTreeSet::new();
    while p.pos < p.tokens.len() {
        let word = p.ident()?;
        match word.as_str() {
            "authority" => {
                if authority.is_some() {
                    return Err("DUPLICATE_AUTHORITY".into());
                }
                p.ident()?;
                p.mark('=')?;
                authority = Some(p.quoted()?);
                p.mark(';')?;
            }
            "subject" => {
                if subject.is_some() {
                    return Err("DUPLICATE_SUBJECT".into());
                }
                let name = p.ident()?;
                p.mark('{')?;
                p.word("repository")?;
                p.mark('=')?;
                let repository = p.quoted()?;
                p.mark(';')?;
                p.word("binding")?;
                p.mark('=')?;
                p.word("exact")?;
                p.mark(';')?;
                p.mark('}')?;
                subject = Some(SubjectDecl {
                    name,
                    repository,
                    binding: "exact".into(),
                });
            }
            "request" => {
                if request.is_some() {
                    return Err("DUPLICATE_REQUEST".into());
                }
                let name = p.ident()?;
                p.mark('{')?;
                p.word("target")?;
                p.mark('=')?;
                let target = p.ident()?;
                p.mark(';')?;
                p.mark('}')?;
                request = Some(RequestDecl { name, target });
            }
            "on" => {
                let event = p.ident()?;
                if !["event", "blocker"].contains(&event.as_str())
                    || !handler_kinds.insert(event.clone())
                {
                    return Err("UNKNOWN_OR_DUPLICATE_HANDLER".into());
                }
                p.mark('{')?;
                let mut statements = Vec::new();
                while !p.at_end_block() {
                    statements.push(p.statement()?);
                }
                p.mark('}')?;
                if statements.is_empty() {
                    return Err("EMPTY_HANDLER".into());
                }
                handlers.push(Handler { event, statements });
            }
            "until" => {
                if dod.is_some() {
                    return Err("DUPLICATE_DOD".into());
                }
                p.mark('{')?;
                let mut predicates = vec![p.ident()?];
                while p.tokens.get(p.pos) == Some(&Token::And) {
                    p.pos += 1;
                    predicates.push(p.ident()?);
                }
                p.mark(';')?;
                p.mark('}')?;
                if predicates.iter().collect::<BTreeSet<_>>().len() != predicates.len() {
                    return Err("DUPLICATE_PREDICATE".into());
                }
                dod = Some(predicates);
            }
            _ => return Err(format!("UNKNOWN_DECLARATION_{word}")),
        }
    }
    let request = request.ok_or("MISSING_REQUEST")?;
    let dod = dod.ok_or("MISSING_DOD")?;
    if handlers.is_empty() {
        return Err("MISSING_HANDLER".into());
    }
    if request.target == "QIKVRT_DOD" {
        let required = [
            "ZERO_BUGS",
            "ALL_PULL_REQUESTS_REGARDED",
            "ALL_BRANCHES_REGARDED",
            "ALL_PRODUCTIVE_BRANCHES_MERGED",
            "FRESH_EXACT_MAIN_VALIDATION_PASS",
            "FRESH_EFFECT_READBACK",
        ];
        if dod.len() != required.len() || required.iter().any(|p| !dod.iter().any(|d| d == p)) {
            return Err("INCOMPLETE_QIKVRT_DOD".into());
        }
    }
    Ok(Program {
        schema: "temdd_ir_v0_1".into(),
        version: "0.1".into(),
        authority: authority.ok_or("MISSING_AUTHORITY")?,
        subject: subject.ok_or("MISSING_SUBJECT")?,
        request,
        handlers,
        dod,
    })
}
