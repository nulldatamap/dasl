// dasl.rs
use std::string::String;
use std::vec::Vec;
use std::str::Chars;

/*
  Syntax (whitespace is ignored):

  expr := '(' name (expr|val)* ')'
  val := symbol|int|bool|string|list|name
  symbol := ':' name
  int := 0..9+
  bool := 'true'|'false'
  string := '"' (escape|char)* '"'
  escape := '\\'|'\n'|'\t'|'\"'
  char := -('\n'|'\r'|'"')
  list := '[' atom* ']'
  ws := ' '|'\n'|'\t'|'\r'
  name := -('"'|':'|'('|'['|']'|')'|ws)-('"'|':'|'('|'['|']'|')'|0..9|ws)+
*/

// This object is going to make peeking characters easier when parsing
struct CharReader<'a> {
  chars : &'a mut Chars<'a>,
  peeked : Option<char>,
}

impl<'a> CharReader<'a> {
  fn new( chrs : &'a mut Chars<'a> ) -> CharReader<'a> {
    return CharReader{ chars: chrs, peeked: None };
  }

  fn peek( &mut self ) -> Option<char> {
    if self.peeked.is_none() {
      self.peeked = self.chars.next();
    }
    self.peeked
  }
}

impl<'a> Iterator<char> for CharReader<'a> {
  fn next( &mut self ) -> Option<char> {
    if self.peeked.is_some() {
      let v = self.peeked;
      self.peeked = None;
      return v;
    }
    return self.chars.next();
  }
}

enum ParseError{
  Expected( String, char ),
  Eof
}

impl ParseError {
  fn get_error_msg( self ) -> String {
    return match self {
      Expected( exp, got ) => format!( "Expected {}, got '{}'.", exp, got ),
      Eof => "Reached EOF too early.".to_string()
    }; 
  }
}

// Code representation of the syntax tree (an AST).
#[deriving(Show)]
enum Lisp {
  Expr( String, Vec<Lisp> ),
  VSymbol( String ),
  VInt( int ),
  VString( String ),
  VList( Vec<Lisp> ),
  VName( String )
}

#[include]
fn fail_parse( err : ParseError ) -> ! {
  fail!( "Parse error: {}", err.get_error_msg() )
}

#[inline]
fn try_parse<T>( val : Result<T, ParseError> ) -> T {
  match val {
    Ok( v ) => return v,
    Err( err ) => fail_parse( err )
  }
}
#[inline]
// Consumes all whitespace, and returns the amount of newlines it encountered
fn skip_whitespace( cr : &mut CharReader ) -> int {
  let mut counter = 0;
  loop {
    match cr.peek() {
      Some( '\n' ) => {
        counter += 1;
        cr.next(); // Consume char
      },
      Some( ' ' ) | Some( '\r' ) | Some( '\t' ) => { 
        cr.next();
      },
      _ => return counter
    }
  }
}

/*
  In order to make parser functions more readable, comments starting
  with "//|" indicate a how for the the syntax the parser is.
  'ws?' optional being whitespace.
*/

static nameChars : &'static [char] = &'static [ '\n', '\r', ' ', '\t', '"'
                                              , ':', '(', ')', '[', ']' ];

fn is_name_char( chr : char ) -> bool {
  return !nameChars.contains( &chr );
}

fn parse_expr<'a>( cr : &mut CharReader, counter : &'a mut int ) -> Result<Lisp, ParseError> {
  //| '(' ws? name ws? (atom|name)* ws? ')'
  
  // We are sure that the current char is '(', so we'll consume it.
  cr.next();
  //| ws? name ws? (atom|name)* ws? ')'
  *counter += skip_whitespace( cr );
  //| name ws? (atom|name)* ws? ')'
  match cr.peek() {
    Some( a ) if !is_name_char( a ) =>
      fail_parse( Expected( "a valid name".to_string(), a ) ),
    None => fail_parse( Eof ),
    _ => ()
  }
  let name = match parse_name( cr, counter ) {
    Ok( nme ) => nme,
    // If 'parse_name' fails, we want another error message
    Err( Eof ) => return Err( Eof ),
    Err( Expected( _, got ) ) => return Err( Expected( "name".to_string(), got ) )
  };
  let mut args = Vec::new();
  //| (ws? atom|name)* ws? ')'
  loop {
    *counter += skip_whitespace( cr );
    // Try to parse either an expression or atom. If any of them fail, we'll ignore it here
    // And handle when we try to match ')'. Eof is still checked though
    let r = match cr.peek() {
      Some( '(' ) =>  parse_expr( cr, counter ),
      Some( a ) => parse_atom( cr, counter ),
      None => return Err( Eof )
    };
    match r {
      Ok( v ) => args.push( v ),
      _ => break
    }
    
  }
  //| ws? ')'
  *counter += skip_whitespace( cr );
  match cr.peek() {
    Some( ')' ) => {
      cr.next();
      return Ok( Expr( name, args ) )
    },
    Some( a ) => return Err( Expected( "'(', an atom or an expression".to_string(), a ) ),
    None => return Err( Eof )
  }
}

fn parse_name<'a>( cr : &mut CharReader, counter : &'a mut int ) -> Result<String, ParseError> {
  let mut buf = String::from_char( 1, cr.next().unwrap() );
  loop {
    match cr.peek() {
      Some( a ) if is_name_char( a ) => buf.push_char( cr.next().unwrap() ),
      _ => return Ok( buf )
    }
  }
}

fn parse_atom<'a>( cr : &mut CharReader, counter : &'a mut int ) -> Result<Lisp, ParseError> {
  match cr.peek() {
    Some( ':' ) => return parse_symbol( cr, counter ),
    //Some( '0'..'9' ) => return parse_int( cr, counter ),
    Some( a ) => return Err( Eof ),
    None => return Err( Eof )
  }
}
/*
fn parse_int<'a>( cr : &mut CharReader, counter : &'a mut int ) -> Result<Lisp, ParseError> {
  // later
}*/

fn parse_symbol<'a>( cr : &mut CharReader, counter : &'a mut int ) -> Result<Lisp, ParseError> {
  cr.next();
  match cr.peek() {
    Some( a ) if !is_name_char( a ) =>
      return Err( Expected( "a valid symbol name".to_string(), a ) ),
    None => return Err( Eof ),
    _ => ()
  }
  return match parse_name( cr, counter ) {
    Ok( nme ) => Ok( VSymbol( nme ) ),
    // If 'parse_name' fails, we want another error message
    Err( Eof ) => Err( Eof ),
    Err( Expected( _, got ) ) => Err( Expected( "name".to_string(), got ) )
  };
}

// Returns a series of ASTs
fn parse( source : String ) -> Vec<Lisp> {
  // We are storing this to insure that it's lifetime spans long enough
  let mut sourceChars = source.as_slice().chars();
  let chars = &mut CharReader::new( &mut sourceChars );
  let mut prg = Vec::new();
  let mut lineCount = 1;

  while true {
    lineCount += skip_whitespace( chars );
    match chars.peek() {
      Some( '(' ) => {
        prg.push( try_parse( parse_expr( chars, &mut lineCount ) ) );
      },
      Some( n ) => {
        fail_parse( Expected( "'('".to_string(), n  ) );
      },
      None => break // We're done, there's nothing left to parse
    }
  }

  return prg;
}

fn main() {
  println!("{}", parse( "(hello :wo (rl :d))(lelmaster :_9001)".to_string() ));
}
