#include <ApplicationServices/ApplicationServices.h>

#define EVENT_LOC kCGHIDEventTap

static int _simulateCommandHotkey( int keyCode )
{
    CGEventRef event[2];

    event[0] = CGEventCreateKeyboardEvent( NULL, (CGKeyCode) keyCode, true );
    event[1] = CGEventCreateKeyboardEvent( NULL, (CGKeyCode) keyCode, false );
    
    CGEventSetFlags( event[0], kCGEventFlagMaskCommand );
    CGEventSetFlags( event[1], kCGEventFlagMaskCommand );

    CGEventPost( EVENT_LOC, event[0] );
    CGEventPost( EVENT_LOC, event[1] );

    CFRelease( event[0] );
    CFRelease( event[1] );

    return 0;
}

int simulateCopy( void )
{
    return _simulateCommandHotkey( 8 );
}

int simulatePaste( void )
{
    return _simulateCommandHotkey( 9 );
}
