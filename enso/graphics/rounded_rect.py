# Copyright (c) 2008, Humanized, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso.graphics.rounded_rect
#
# ----------------------------------------------------------------------------

"""
    Functions and constants for drawing rounded rectangles.
"""

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

LOWER_RIGHT = 0
UPPER_RIGHT = 1
LOWER_LEFT = 2
UPPER_LEFT = 3
ALL_CORNERS = [LOWER_RIGHT, UPPER_RIGHT, LOWER_LEFT, UPPER_LEFT]

# The radius of a corner of a rounded rectangle, in points.
CORNER_RADIUS = 5


# ----------------------------------------------------------------------------
# Public Functions
# ----------------------------------------------------------------------------

def drawRoundedRect(context, rect, softenedCorners, radius=CORNER_RADIUS):
    """
    Draws a rectangle where each corner in softenedCorners has
    a CORNER_RADIUS-unit radius arc instead of a corner.

    If softenedCorners parameter is dictionary instead of a list, the item
    key identifies the corner and the value identifies the radius of that
    corner. This way all four corners can have different radiuses.
    Set the value to None for default radius.
    """

    PI = 3.1415926535
    context.new_path()

    xPos, yPos, width, height = rect

    if LOWER_RIGHT in softenedCorners:
        # Included in list, want round radius
        try:
            # Is the specific radius for this corner specified?
            lower_right_radius = softenedCorners.get(LOWER_RIGHT)
            if lower_right_radius is None:
                lower_right_radius = radius
        except:
            # Set default radius
            lower_right_radius = radius
    else:
        # Not included in list, no round radius
        lower_right_radius = 0

    if LOWER_LEFT in softenedCorners:
        # Included in list, want round radius
        try:
            # Is the specific radius for this corner specified?
            lower_left_radius = softenedCorners.get(LOWER_LEFT)
            if lower_left_radius is None:
                lower_left_radius = radius
        except:
            # Set default radius
            lower_left_radius = radius
    else:
        # Not included in list, no round radius
        lower_left_radius = 0

    if UPPER_LEFT in softenedCorners:
        # Included in list, want round radius
        try:
            # Is the specific radius for this corner specified?
            upper_left_radius = softenedCorners.get(UPPER_LEFT)
            if upper_left_radius is None:
                upper_left_radius = radius
        except:
            # Set default radius
            upper_left_radius = radius
    else:
        # Not included in list, no round radius
        upper_left_radius = 0

    if UPPER_RIGHT in softenedCorners:
        # Included in list, want round radius
        try:
            # Is the specific radius for this corner specified?
            upper_right_radius = softenedCorners.get(UPPER_RIGHT)
            if upper_right_radius is None:
                upper_right_radius = radius
        except:
            # Set default radius
            upper_right_radius = radius
    else:
        # Not included in list, no round radius
        upper_right_radius = 0

    if lower_right_radius > 0:
        context.arc(xPos + width - lower_right_radius,
                    yPos + height - lower_right_radius,
                    lower_right_radius,
                    0,
                    .5 * PI)
    else:
        context.move_to(xPos + width, yPos + height)

    context.line_to(xPos + lower_left_radius, yPos + height)

    if lower_left_radius > 0:
        context.arc(xPos + lower_left_radius,
                    yPos + height - lower_left_radius,
                    lower_left_radius,
                    .5 * PI,
                    PI)

    context.line_to(xPos, yPos + upper_left_radius - 1)

    if upper_left_radius > 0:
        context.arc(xPos + upper_left_radius,
                    yPos + upper_left_radius,
                    upper_left_radius,
                    PI,
                    1.5 * PI)

    context.line_to(xPos + width - upper_right_radius, yPos)

    if upper_right_radius > 0:
        context.arc(xPos + width - upper_right_radius,
                    yPos + upper_right_radius,
                    upper_right_radius,
                    1.5 * PI,
                    2 * PI)

    context.line_to(xPos + width, yPos + height - lower_right_radius)
