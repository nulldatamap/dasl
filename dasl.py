import random

__func_name__ = None
__func_args__ = None
__func_locals__ = None
__arg_off__ = 0
__context__ = "code"
__static_data__ = {}
__hwq_enabled__ = False

dual_ops = [ "add", "sub", "mul", "div", "mli", "dvi", "mod"
           , "bor", "xor", "shr", "shl", "adx", "sbx", "band" ]

if_ops = [ "ifb", "ifc", "ife", "ifn", "ifg", "ifa", "ifl", "ifu" ]

hwq_a = None
hwq_b = None
hwq_c = None
hwq_x = None
hwq_y = None

ORDERING = [ "boot", "decl", "code", "func", "data" ]

class Decl(object):
  def __init__( self, name ):
    self.name = name
    self.defined = False
    self.argc = 0

  def define( self ):
    if self.defined:
      raise Exception( "Variables can't be redefined, use 'setv'." )
    self.defined = True

  def __str__( self ):
    if not self.defined:
      raise Exception( "Undefined variable " + self.name + "." )
    return "[_{}]".format( self.name )

class Func(object):
  def __init__( self, name ):
    self.name = name
    self.defined = False

  def define( self ):
    if self.defined:
      raise Exception( "functions can't be redefined." )
    self.defined = True

  def __str__( self ):
    if not self.defined:
      raise Exception( "Undefined function " + self.name + "." )
    return "_" + self.name

def macro( f ):
  f.__macro__ = True
  return f

def compile( f ):
  return finalize( f() )

def lisp( prg ):
  if type( prg ) != tuple:
    return prg
  f = prg[0]
  if type( f ) == Func:
    return call( *prg )
  if hasattr( f, "__macro__" ):
    return f( *prg[1:] )
  return f( *map( lisp, prg[1:] ) )

def rvar( v ):
  return Decl( v )

def rfunc( v ):
  return Func( v )

def varpool( *vs ):
  return ( Decl( v ) for v in vs )

def funcpool( *vs ):
  return ( Func( v ) for v in vs )

def code( c ):
  global __context__
  return ( __context__, c )

def enable_hwq():
  global hwq_a, hwq_b, hwq_c, hwq_x, hwq_y, __hwq_enabled__
  if __hwq_enabled__:
    return
  __hwq_enabled__ = True
  hwq_a = Decl( "hwq_a" )
  hwq_b = Decl( "hwq_b" )
  hwq_c = Decl( "hwq_c" )
  hwq_x = Decl( "hwq_x" )
  hwq_y = Decl( "hwq_y" )
  return hwq_a, hwq_b, hwq_c, hwq_x, hwq_y

def program( *cde ):
  global __static_data__, __hwq_enabled__
  # Get the variables that will be overshadowed
  bootseg = [ ( "boot", "set pc, boot" ), ( "code", ":boot" ) ]
  hltseg = [ code( "set a, a" ), code( ":hlt set pc, hlt" ) ]
  if __hwq_enabled__:
    bootseg += let( hwq_a, 0 )
    bootseg += let( hwq_b, 0 )
    bootseg += let( hwq_c, 0 )
    bootseg += let( hwq_x, 0 )
    bootseg += let( hwq_y, 0 )
  __static_data__ = {}
  usrcode = do( *cde )
  dataseg = []
  for data in __static_data__:
    de = __static_data__[data]
    dataseg.append( ( "data", ":__data_{} dat {}".format( shash( de ), static_data_to_source( de ) ) ) )
  return bootseg + usrcode + hltseg + dataseg

def shash( v ):
  return str( hash( v ) ).replace( "-", "_" )

def to_hashable( l ):
  for i in l:
    if type( i ) != int:
      raise Exception( "Only static int list allowed for lists." )
  return tuple( l )

def static_data_to_source( sd ):
  r = str( len( sd ) ) + ", "
  if type( sd ) == str:
    return r + '"{}"'.format( sd.replace( '"', '", 34, "' ) )
  else:
    for i in sd:
      r += str( i ) + ", "
    return r[:-2]

def do( *sts ):
  return reduce( lambda x,y: x+ lisp( y ), sts, [] )

def finalize( prg ):
  return reduce( lambda v, w: v + w[1] + "\n", reduce( lambda x, y: x+y, map( lambda x: filter( lambda s: s[0]==x, prg ), ORDERING ) ), "" )

def is_static_value( v ):
  return type( v ) in [ int, str, list ]

def static_data_entry( d ):
  global __static_data__
  if type( d ) == str:
    if not d in __static_data__:
      __static_data__[d] = d
    return "__data_" + shash( d )
  elif type( d ) == list:
    hd = to_hashable( d )
    if not hd in __static_data__:
      __static_data__[hd] = hd
    return "__data_" + shash( hd )


def checkarg( arg ):
  global __static_data__
  if type( arg ) in [ int, tuple, Decl, Func ]:
    return arg
  if type( arg ) == bool:
    return int( arg )
  if type( arg ) in [ str, list ]:
    return static_data_entry( arg )
  raise Exception( "Invalid value given: " + str( type( arg ) ) )

def argcheck( f ):
  def wrapper( *args ):
    nargs = []
    for arg in args:
      nargs.append( checkarg( arg ) )
    return f( *nargs )
  return wrapper

# DCPU instructions
@argcheck
def let( vn, vl ): 
  if type( vn ) != Decl:
    raise Exception( "'let' can only define variables." )
  if not is_static_value( vl ):
    raise Exception( "'let' can only defined variables to a static value." )
  vn.define()
  return [ ( "decl", ":_" + vn.name + " dat " + str( vl ) ) ]

@macro
@argcheck
def setv( vn, vl ):
  if type( vn ) != Decl:
    raise Exception( "'setv' can only assign to variables." )
  pc = []
  if type( vl ) == tuple:
    pc = do( vl )
    vl = 'a'
  return pc + [ code( "set {}, {}".format( vn, vl ) ) ] 

@macro
@argcheck
def _loadv( v ):
  return [ code( "set a, " + str( v ) ) ]

@macro
@argcheck
def setm( ma, mv ):
  if type( ma ) == Decl:
    ma = ( _loadv, ma )
  ta = type( ma ) == tuple
  tv = type( mv ) == tuple
  if ta and not tv:
    return do( ma ) + [ code( "set [a], " + str( mv ) ) ]
  elif tv and not ta:
    return do( mv ) + [ code( "set [{}], a".format( ma ) ) ]
  elif ta and tv:
    return do( ma ) + [ code( "set b, a" ) ] + do( mv ) + [ code( "set [b], a" ) ]
  else:
    return [ code( "set [{}], {}".format( ma, mv ) ) ]

@macro
@argcheck
def getm( ma ):
  if type( ma ) == Decl:
    ma = ( _loadv, ma )
  if type( ma ) == tuple:
    return do( ma ) + [ code( "set a, [a]" ) ]
  else:
    return [ code( "set a, [{}]".fomrat( ma ) ) ]

@macro
@argcheck
def begin( *args ):
  r = []
  for arg in args:
    if type( arg ) != tuple:
      r += do( (_loadv, arg) )
    else:
      r += do( arg )
  return r

@macro
def dual_op( op, x, y ):
  x = checkarg( x )
  y = checkarg( y )
  tx = type( x ) == tuple
  ty = type( y ) == tuple
  if tx and not ty:
    return do( x ) + [ code( op + " a, " + str( y ) ) ]
  elif ty and not ty:
    return do( y ) + [ code( op + " a, " + str( x ) ) ]
  elif tx and ty:
    return do( x ) + [ code( "set b, a" ) ] + do( y ) + [ code( op + " a, b" ) ]
  else:
    return [ code( "set a, " + str( x ) ), code( op + " a, " + str( y ) ) ]

# define dual ops
for dop in dual_ops:
  exec "@macro\ndef {0}( x, y ):\n\treturn dual_op( '{0}', x, y )".format( dop )

def is_if_op( op ):
  if len( op ) == 0:
    return False
  return op[0][1][:3] in if_ops

@macro
def if_op( op, x, y, thn, els ):
  # ife x, y
  #   set pc, __then ; Unless then is 1 instruction, or an if op
  # elsecode
  # set pc, __end
  # :__then
  # thencode
  # :__end
  x = checkarg( x )
  y = checkarg( y )
  thn = checkarg( thn )
  els = checkarg( els )
  ifid = str( random.randint( 0, 2**32 ) )
  if type( thn ) != tuple:
    thn = ( _loadv, thn )
  thn = do( thn )
  if type( els ) != tuple:
    els = ( _loadv, els )
  tx = type( x ) == tuple
  ty = type( y ) == tuple
  pc = []
  ifc = [ code( op + " {}, {}".format( x, y ) ) ]
  ifb = []
  if tx and not ty:
    pc = do( x )
    ifc[0] = code( op + " a, {}".format( y ) )
  elif ty and not tx:
    pc = do( y )
    ifc[0] = code( op + " {}, a".format( x ) )
  elif tx and ty:
    pc = do( x ) + [ code( "set b, a" ) ] + do( y )
    ifc[0] = code( op + " b, a" )
  inlined = False
  endlabel = "__if_end_" + ifid
  if is_if_op( thn ):
    ifb = thn
    inlined = True
  else:
    thenlabel = "__if_then_" + ifid
    ifb = [ code( "set pc, " + thenlabel ) ]
  if not inlined:
    ifb += do( els )
    ifb += [ code( "set pc, " + endlabel ), code( ":" + thenlabel ) ] + thn
    ifb += [ code( ":" + endlabel ) ]
  else:
    ifb += [ code( "set pc, " + endlabel ), do( els ), code( ":" + endlabel ) ]
  return pc + ifc + ifb

# define if ops
for iop in if_ops:
  exec "@macro\ndef {0}( x, y, thn, els ):\n\treturn if_op( '{0}', x, y, thn, els )".format( iop )

def arg( x ):
  global __context__, __arg_off__
  if __context__ != "func":
    raise Exception( "Can't call 'arg' outside a function." )
  if not type( x ) in [ str, int ]:
    raise Exception( "The argument for 'arg' must be either an index or name." )
  if type( x ) == str and not x in __func_args__:
    raise Exception( "No argument named '{}' in '{}'".format( x, __func_name__ ) )
  elif type( x ) == str:
    x = __func_args__.index( x )
  if x >= len( __func_args__ ) or x < 0:
    raise Exception( "Invalid argument index {}, "
                   + "out of bounds in '{}' ( {} arguemnts )."
                      .format( x, __func_name__, len( __func_args__ ) ) )
  a = x + 1 + len( __func_locals__ ) + __arg_off__
  if a < 0:
    a += 0x10000
  return [ code( "set a, [SP+{}]".format( a ) ) ]


def getl( x ):
  global __context__, __arg_off__
  if __context__ != "func":
    raise Exception( "Can't call 'getl' outside a function." )
  if not type( x ) in [ str, int ]:
    raise Exception( "The argument for 'getl' must be either an index or name." )
  if type( x ) == str and not x in __func_locals__:
    raise Exception( "No local named '{}' in '{}'".format( x, __func_name__ ) )
  elif type( x ) == str:
    x = __func_locals__.index( x )
  if x >= len( __func_locals__ ) or x < 0:
    raise Exception( "Invalid local index {}, "
                   + "out of bounds in '{}' ( {} arguemnts )."
                      .format( x, __func_name__, len( __func_locals__ ) ) )
  a = x + 1 + __arg_off__
  if a < 0:
    a += 0x10000
  return [ code( "set a, [SP+{}]".format( a ) ) ]

@macro
def setl( x, v ):
  global __context__, __arg_off__
  v = checkarg( v )
  if __context__ != "func":
    raise Exception( "Can't call 'setl' outside a function." )
  if not type( x ) in [ str, int ]:
    raise Exception( "The argument for 'setl' must be either an index or name." )
  if type( x ) == str and not x in __func_locals__:
    raise Exception( "No local named '{}' in '{}'".format( x, __func_name__ ) )
  elif type( x ) == str:
    x = __func_locals__.index( x )
  if x >= len( __func_locals__ ) or x < 0:
    raise Exception( "Invalid local index {}, "
                   + "out of bounds in '{}' ( {} arguemnts )."
                      .format( x, __func_name__, len( __func_locals__ ) ) )
  a = x + 1 + __arg_off__
  if a < 0:
    a += 0x10000
  if type( v ) == tuple:
    return do( v ) + [ code( "set [SP+{}], a".format( a ) ) ]
  return [ code( "set [SP+{}], {}".format( a, v ) ) ]


def hwn():
  return [ code( "hwn a" ) ]

@macro
def hwq( x ):
  pc = [ code( "hwq " + str( x ) ) ]
  if type( x ) == tuple:
    pc = do( x ) + [ code( "hwq a" ) ]
  b = [ code( "set [_hwq_a], a" )
      , code( "set [_hwq_b], b" )
      , code( "set [_hwq_c], c" )
      , code( "set [_hwq_x], x" )
      , code( "set [_hwq_y], y" ) ]
  return pc + b

@macro
@argcheck
def hwi( x ):
  if type( x ) == tuple:
    return do( x ) + [ code( "hwi a" ) ]
  else:
    return [ code( "hwi " + str( x ) ) ]

@macro
def defn( fn, fa, lcs, fb ):
  global __func_name__, __func_args__, __context__, __func_locals__
  if __context__ == "func":
    raise Exception( "Nested function definitions are not allowed." )
  if type( fn ) != Func:
    raise Exception( "'defn' can only define functions." )
  fn.define()
  fn.argc = len( fa )
  fn.localc = len( lcs )
  __context__ = "func"
  __func_name__ = fn
  __func_args__ = list( reversed( fa ) )
  __func_locals__ = lcs
  fheader = [ code( ":" + str( fn ) ) ]
  if fn.localc != 0:
    fheader.append( code( "sub sp, " + str( fn.localc ) ) )
  if ( fn.argc + fn.localc ) == 0:
    ffooter = [ code( "set pc, pop" ) ]
  else:
    ffooter = [ code( "add sp, " + str( fn.localc ) )
              , code( "set z, pop" )
              , code( "add sp, " + str( fn.argc ) )
              , code( "set pc, z" ) ]
  r = fheader + do( fb ) + ffooter
  __context__ = "code"
  __func_name__ = None
  __func_args__ = None
  __func_locals__ = None
  return r

@macro
@argcheck
def call( fn, *args ):
  global __arg_off__
  pc = []
  if fn.argc != len( args ):
    raise Exception( "Expected {} for the {}. argument in {} ( got {} ).".format( fn.argc, fn, len( args ) ) )
  for argi in xrange( len( args ) ):
    arg = args[argi]
    if type( arg ) == tuple:
      pc += do( arg ) + [ code( "set push, a" ) ]
      __arg_off__ += 1
    else:
      if type( arg ) != Decl and not is_static_value( arg ):
        raise Exception( "'{}'s {}. argument must be a static value.".format( fn, argi ) ) 
      pc += [ code( "set push, " + str( arg ) ) ]
      __arg_off__ += 1
  __arg_off__ = 0
  return pc + [ code( "jsr " + str( fn ) ) ]

@macro
@argcheck
def recur( *args ):
  global __arg_off__
  if __context__ != "func":
    raise Exception( "Can't recurse outside of a function." )
  if len( args ) != len( __func_args__ ):
    raise Exception( "Expected {} for the {}. argument in {} ( got {} ).".format( len( __func_args__ ), __func_name__, len( args ) ) )
  backa = len( __func_locals__ ) + len( __func_args__ ) + 1
  pc = [ code( "add SP, " + str( backa ) ) ]
  for argi in xrange( len( args ) ):
    __arg_off__ = (-backa) + argi
    arg = args[argi]
    if type( arg ) == tuple:
      pc += do( arg ) + [ code( "set push, a" ) ]
    else:
      if type( arg ) != Decl and not is_static_value( arg ):
        raise Exception( "'{}'s {}. argument must be a static value.".format( __func_name__, argi ) ) 
      pc += [ code( "set push, " + str( arg ) ) ]
  __arg_off__ = 0
  return pc + [ code( "sub SP, 1" ), code( "set pc, " + str( __func_name__ ) ) ]
