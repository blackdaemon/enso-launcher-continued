#include <Python.h>
#include <cairo-quartz.h>
#include "pycairo.h"

#import <AppKit/NSGraphicsContext.h>

typedef struct {
	PyObject_HEAD
	__strong id objc_object;
	int 	    flags;
} PyObjCObject;

static Pycairo_CAPI_t *Pycairo_CAPI;

static PyObject *cairo_surface_from_NSGraphicsContext( PyObject *self,
                                                       PyObject *args )
{
    PyObjCObject *obj;
    unsigned int width;
    unsigned int height;

    if ( !PyArg_ParseTuple( args, "OII", (PyObject **) &obj,
                            &width, &height ) )
        return NULL;

    NSGraphicsContext *nsContext = (NSGraphicsContext *) obj->objc_object;
    CGContextRef cgContext = [nsContext graphicsPort];

    cairo_surface_t *surface = cairo_quartz_surface_create_for_cg_context(
        cgContext,
        width,
        height
        );

    PyObject *pycairoSurface;

    pycairoSurface = PycairoSurface_FromSurface( surface, NULL );

    if ( pycairoSurface == NULL )
    {
        /* TODO: Cleanup */
        /* PycairoSurface_FromSurface() has already set the
           Python error state. */
        return NULL;
    }

    return pycairoSurface;
}

static PyMethodDef quartz_cairo_bridge_methods[] = {
    { "cairo_surface_from_NSGraphicsContext",
      cairo_surface_from_NSGraphicsContext,
      METH_VARARGS,
      "Convert a NSGraphicsContext object to a Cairo surface." },
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initquartz_cairo_bridge( void )
{
    Py_InitModule( "enso.platform.osx.quartz_cairo_bridge",
                   quartz_cairo_bridge_methods );

    Pycairo_IMPORT;
}
