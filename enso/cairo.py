import enso.providers

__cairoImpl = enso.providers.get_interface( "cairo" )

globals().update( __cairoImpl.__dict__ )
