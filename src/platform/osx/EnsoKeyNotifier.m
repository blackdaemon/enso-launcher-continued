#include <AppKit/NSWorkspace.h>
#include <ApplicationServices/ApplicationServices.h>
#import <Foundation/NSAutoreleasePool.h>
#import <Foundation/NSDistributedNotificationCenter.h>
#import <Foundation/NSArray.h>
#import <Foundation/NSDictionary.h>
#import <Foundation/NSString.h>
#include <stdio.h>

#define QUASIMODE_KEY kCGEventFlagMaskAlternate

#ifdef DEBUG
#define DEBUG_MSG( msg ) printf( msg );
#else
#define DEBUG_MSG( msg )
#endif

NSDistributedNotificationCenter *center;

CGKeyCode lastQuasimodalKeyCode;
CGEventFlags lastQuasimodalKeyFlags;
int numQuasimodalKeyDowns = 0;

static BOOL inQuasimode = NO;

static void sendSomeKeyEvent( void )
{
    NSArray *keys = [NSArray arrayWithObjects: @"event", nil];
    NSArray *values = [NSArray arrayWithObjects: @"someKey", nil];
    NSDictionary *dict = [NSDictionary dictionaryWithObjects: values forKeys: keys];

    [center postNotificationName: @"EnsoKeyNotifier_msg"
            object: @"EnsoKeyNotifier"
            userInfo: dict];
}

CGEventRef processEvent( CGEventTapProxy proxy,
                         CGEventType type,
                         CGEventRef event,
                         void *refcon )
{
    //int64_t keycode = CGEventGetIntegerValueField(
    //    event,
    //    kCGKeyboardEventKeycode
    //    );

    BOOL passOnEvent = !inQuasimode;

    if ( type == kCGEventFlagsChanged )
    {
        CGEventFlags flags = CGEventGetFlags( event );

        if ( inQuasimode )
        {
            if ( !(flags & QUASIMODE_KEY) )
            {
                NSArray *keys = [NSArray arrayWithObjects: @"event", nil];
                NSArray *values = [NSArray arrayWithObjects: @"quasimodeEnd", nil];
                NSDictionary *dict = [NSDictionary dictionaryWithObjects: values forKeys: keys];

                [center postNotificationName: @"EnsoKeyNotifier_msg"
                        object: @"EnsoKeyNotifier"
                        userInfo: dict];
                inQuasimode = NO;
                if ( numQuasimodalKeyDowns == 1 )
                {
                    CGEventRef event[2];

                    DEBUG_MSG( "Re-posting single keypress\n" );

                    event[0] = CGEventCreateKeyboardEvent(
                        NULL,
                        (CGKeyCode) lastQuasimodalKeyCode,
                        true
                        );

                    event[1] = CGEventCreateKeyboardEvent(
                        NULL,
                        (CGKeyCode) lastQuasimodalKeyCode,
                        false
                        );

                    CGEventSetFlags( event[0], lastQuasimodalKeyFlags );
                    CGEventSetFlags( event[1], lastQuasimodalKeyFlags );

                    CGEventTapPostEvent( proxy, event[0] );
                    CGEventTapPostEvent( proxy, event[1] );

                    CFRelease( event[0] );
                    CFRelease( event[1] );
                }
                DEBUG_MSG( "Exit quasimode\n" );
            }
        } else {
            if ( flags & QUASIMODE_KEY )
            {
                NSArray *keys = [NSArray arrayWithObjects: @"event", nil];
                NSArray *values = [NSArray arrayWithObjects: @"quasimodeStart", nil];
                NSDictionary *dict = [NSDictionary dictionaryWithObjects: values forKeys: keys];

                [center postNotificationName: @"EnsoKeyNotifier_msg"
                        object: @"EnsoKeyNotifier"
                        userInfo: dict];
                inQuasimode = YES;
                passOnEvent = NO;
                numQuasimodalKeyDowns = 0;
                DEBUG_MSG( "Enter quasimode\n" );
            } else {
                sendSomeKeyEvent();
            }
        }
    } else {
        /* Key up/down event */

        if ( inQuasimode )
        {
#define MAX_STR_LEN 10
        
            UniChar strbuf[MAX_STR_LEN];
            UniCharCount charsCopied;

            CGEventKeyboardGetUnicodeString(
                event,
                MAX_STR_LEN,
                &charsCopied,
                strbuf
                );

            NSString *chars = [NSString stringWithCharacters: strbuf
                                        length: charsCopied];
            NSString *eventType;

            int64_t keycode = CGEventGetIntegerValueField(
                event,
                kCGKeyboardEventKeycode
                );

            if ( type == kCGEventKeyDown ) {
                numQuasimodalKeyDowns += 1;
                lastQuasimodalKeyCode = keycode;
                lastQuasimodalKeyFlags = CGEventGetFlags( event );
                eventType = @"keyDown";
            } else
                eventType = @"keyUp";

            NSNumber *keycodeNum = [NSNumber numberWithUnsignedInt: keycode];

            NSArray *keys = [NSArray arrayWithObjects: @"event", @"chars", @"keycode", nil];
            NSArray *values = [NSArray arrayWithObjects: eventType, chars, keycodeNum, nil];
            NSDictionary *dict = [NSDictionary dictionaryWithObjects: values forKeys: keys];

            [center postNotificationName: @"EnsoKeyNotifier_msg"
                    object: @"EnsoKeyNotifier"
                    userInfo: dict];
        } else {
            sendSomeKeyEvent();
        }
    }

    if ( passOnEvent )
        return event;
    else
        return NULL;
}

CGEventRef myCallback( CGEventTapProxy proxy,
                       CGEventType type,
                       CGEventRef event,
                       void *refcon )
{
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    CGEventRef retval;
    NSString *bundleId = [[[NSWorkspace sharedWorkspace] activeApplication] objectForKey: @"NSApplicationBundleIdentifier"];

    if (bundleId &&
        [bundleId isEqualToString: @"com.blizzard.worldofwarcraft"])
    {
        retval = event;
    } else {
        retval = processEvent(proxy, type, event, refcon);
    }

    [pool release];

    return retval;
}

int main( int argc, const char *argv[] )
{
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];

    center = [NSDistributedNotificationCenter defaultCenter];

    CGEventMask mask = ( CGEventMaskBit( kCGEventKeyDown ) |
                         CGEventMaskBit( kCGEventKeyUp ) |
                         CGEventMaskBit( kCGEventFlagsChanged ) );

    CFMachPortRef portRef = CGEventTapCreate(
        //kCGSessionEventTap,
        kCGHIDEventTap,
        kCGHeadInsertEventTap,
        0,
        mask,
        myCallback,
        NULL
        );

    CFRunLoopSourceRef rlSrcRef;

    if ( portRef == NULL )
    {
        printf( "CGEventTapCreate() failed.\n" );
        return -1;
    }

    rlSrcRef = CFMachPortCreateRunLoopSource(
        kCFAllocatorDefault,
        portRef,
        0
        );

    CFRunLoopAddSource(
        CFRunLoopGetCurrent(),
        rlSrcRef,
        kCFRunLoopDefaultMode
        );

    printf( "Greetings from %s.\n", argv[0] );
    printf( "Please make sure either of the following is true:\n\n" 
            "  (1) This program is running with super-user privileges.\n"
            "  (2) Access for assistive devices is enabled in the \n"
            "      Universal Access System Preferences.\n\n"
            "If one or more of these conditions is not satisfied, then "
            "quasimodal keypresses will not be recognized.\n" );

    printf( "Running event loop...\n" );

    //CFRunLoopRunInMode( kCFRunLoopDefaultMode, 10.0, false );
    CFRunLoopRun();

    printf( "Done running event loop.\n" );

    CFRunLoopRemoveSource(
        CFRunLoopGetCurrent(),
        rlSrcRef,
        kCFRunLoopDefaultMode
        );

    CFRelease( rlSrcRef );
    CFRelease( portRef );

    [pool release];

    return 0;
}
