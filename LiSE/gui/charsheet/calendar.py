# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from kivy.clock import Clock
from kivy.properties import (
    BooleanProperty,
    BoundedNumericProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.layout import Layout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget

from LiSE.data import (
    THING_CAL,
    PLACE_CAL,
    PORTAL_CAL,
    CHAR_CAL)


SCROLL_FACTOR = 4


def get_timeline_x(calendar, branch):
    return ((branch - calendar.branch) * calendar.col_width
            + calendar.xmov + calendar.x)


def get_timeline_y(calendar, tick):
    return calendar.ymov + calendar.top + calendar.y - (
        tick - calendar.tick) * calendar.tick_height


class ColorBox(BoxLayout):
    """A BoxLayout with a background of a particular color.

    In lise.kv this is filled with a label."""
    color = ListProperty()


class Cell(RelativeLayout):
    """A box to represent an event on the calendar.

    It needs a branch, tick_from, tick_to, text, and a calendar to belong
    to.

    """
    active = BooleanProperty(False)
    branch = NumericProperty()
    calendar = ObjectProperty()
    text = StringProperty()
    tick_from = NumericProperty()
    tick_to = NumericProperty(None, allownone=True)


class Timeline(Widget):
    """A line drawn atop one of the columns of the calendar, representing
    the present moment.

    """

    def upd_branch(self, calendar, branch):
        self.x = get_timeline_x(calendar, branch)

    def upd_tick(self, calendar, tick):
        self.y = get_timeline_y(calendar, tick)

    def upd_time(self, calendar, branch, tick):
        self.upd_branch(calendar, branch)
        self.upd_tick(calendar, tick)


class Calendar(Layout):
    """A gridlike layout of cells representing events throughout every
    branch of the timestream.

    It will fill itself in based on what it finds in the Skeleton under
    the given keys. Only the events that can be seen at the moment, and a
    few just out of view, will be instantiated.

    It may be scrolled by dragging. It will snap to some particular branch
    and tick when dropped.

    A timeline will be drawn on top of it, but that is not instantiated
    here. Look in CalendarView below.

    """
    boneatt = StringProperty()
    branch = NumericProperty(0)
    branches_offscreen = NumericProperty(2)
    branches_wide = NumericProperty()
    cal_type = NumericProperty()
    character = ObjectProperty()
    col_width = NumericProperty()
    completedness = NumericProperty()
    font_name = StringProperty()
    font_size = NumericProperty()
    force_refresh = BooleanProperty(False)
    i = NumericProperty()
    key = StringProperty()
    referent = ObjectProperty(None)
    skel = ObjectProperty(None)
    spacing_x = NumericProperty()
    spacing_y = NumericProperty()
    stat = StringProperty()
    tick = BoundedNumericProperty(0, min=0)
    tick_height = NumericProperty()
    ticks_tall = NumericProperty(100)
    ticks_offscreen = NumericProperty(0)
    timeline = ObjectProperty()
    xcess = NumericProperty(0)
    xmov = NumericProperty(0)
    ycess = NumericProperty(0)
    ymov = NumericProperty(0)

    def on_character(self, i, v):
        """Count toward completion"""
        self.completedness += 1

    def on_keys(self, i, v):
        """Count toward completion"""
        self.completedness += 1

    def on_timeline(self, i, v):
        """Count toward completion"""
        self.completedness += 1

    def on_completedness(self, i, v):
        """When I have everything I need to fetch everything I'm missing, call
        self.completed().

        """
        if v == 3:
            self.completed()

    def completed(self):
        """Collect my referent--the object I am about--and my skel--the
        portion of the great Skeleton that pertains to my
        referent. Arrange to be notified whenever I need to lay myself
        out again.

        """
        character = self.character
        closet = character.closet

        def upd_time(branch, tick):
            self.timeline.upd_branch(self, branch)
            self.timeline.upd_tick(self, tick)
        closet.register_time_listener(upd_time)
        self.bind(
            size=lambda i, v: self.timeline.upd_time(
                self, closet.branch, closet.tick),
            pos=lambda i, v: self.timeline.upd_time(
                self, closet.branch, closet.tick),
            xmov=lambda i, v: self.timeline.upd_branch(self, closet.branch),
            ymov=lambda i, v: self.timeline.upd_tick(self, closet.tick))
        self.timeline.upd_time(
            self, closet.branch, closet.tick)
        skeleton = closet.skeleton
        if self.cal_type == THING_CAL:
            self.referent = self.character.get_thing(self.key)
            if self.stat == "location":
                self.skel = skeleton["thing_loc"][
                    unicode(self.character)][self.key]
            else:
                self.skel = skeleton["thing_stat"][
                    unicode(self.character)][self.key][self.stat]
        elif self.cal_type == PLACE_CAL:
            self.referent = self.character.get_place(self.key)
            self.skel = skeleton["place_stat"][
                unicode(self.character)][self.key][self.stat]
        elif self.cal_type == PORTAL_CAL:
            if self.stat in ("origin", "destination"):
                self.skel = skeleton["portal_loc"][
                    unicode(self.character)][self.key]
            else:
                self.skel = skeleton["portal_stat"][
                    unicode(self.character)][self.key][self.stat]
        elif self.cal_type == CHAR_CAL:
            self.skel = skeleton["character_stat"][
                unicode(self.character)][self.key]
        else:
            raise NotImplementedError
        self.skel.register_set_listener(self.refresh_and_layout)
        self.skel.register_del_listener(self.refresh_and_layout)
        self.bind(size=lambda i, v: self._trigger_layout(),
                  pos=lambda i, v: self._trigger_layout())
        Clock.schedule_once(self.refresh_and_layout, 0)

    def refresh_and_layout(self, *args):
        """Get rid of my current widgets and make new ones."""
        self.clear_widgets()
        self.force_refresh = True
        self._trigger_layout()

    def branch_x(self, b):
        """Where does the column representing that branch have its left
edge?"""
        b -= self.branch
        return self.x + self.xmov + b * self.col_width

    def tick_y(self, t):
        """Where upon me does the given tick appear?

That's where you'd draw the timeline for it."""
        if t is None:
            return self.y
        else:
            t -= self.tick
            return self.y + self.ymov + self.height - self.tick_height * t

    def refresh(self):
        """Generate cells that are missing. Remove cells that cannot be
        seen."""
        minbranch = int(self.branch - self.branches_offscreen)
        maxbranch = int(
            self.branch + self.branches_wide + self.branches_offscreen)
        mintick = int(self.tick - self.ticks_offscreen)
        maxtick = int(self.tick + self.ticks_tall + self.ticks_offscreen)
        old_widgets = {}
        for child in self.children:
            old_widgets[child.bone] = child
        self.clear_widgets()
        for branch in xrange(minbranch, maxbranch):
            if branch not in self.skel:
                continue
            boneiter = self.skel[branch].iterbones()
            prev = next(boneiter)
            for bone in boneiter:
                if bone in old_widgets:
                    self.add_widget(old_widgets[bone])
                    print("refreshing w. old bone: {}".format(bone))
                elif (
                        prev.tick < maxtick and
                        bone.tick > mintick):
                    print("refreshing w. new bone: {}".format(bone))
                    cell = Cell(
                        calendar=self,
                        branch=branch,
                        text=getattr(prev, self.boneatt),
                        tick_from=prev.tick,
                        tick_to=bone.tick)
                    cell.bone = bone
                    self.add_widget(cell)
                if bone.tick > maxtick:
                    break
                prev = bone
            # The last cell is infinitely long
            if prev.tick < maxtick:
                if self.cal_type == 5:
                    text = prev.location
                elif self.cal_type == 6:
                    text = prev.place
                elif self.cal_type == 7:
                    text = "{}->{}".format(
                        prev.origin, prev.destination)
                elif self.cal_type == 8:
                    text = prev.value
                else:
                    text = ""
                assert(text is not None)
                self.add_widget(Cell(
                    calendar=self,
                    branch=branch,
                    text=text,
                    tick_from=prev.tick,
                    tick_to=None))

    def do_layout(self, *largs):
        """Arrange all the cells into columns sorted by branch, and stack them
as appropriate to their start and end times. Adjust for scrolling as
necessary."""
        if self.parent is None:
            return
        branchwidth = self.col_width
        d_branch = int(self.xmov / branchwidth)
        tickheight = self.tick_height
        d_tick = int(self.ymov / tickheight)
        if abs(d_branch) >= 1 or abs(d_tick) >= 1:
            try:
                self.branch -= d_branch
            except ValueError:
                self.branch = 0
            self.xmov -= d_branch * (branchwidth + self.spacing_y)
            try:
                self.tick += d_tick
            except ValueError:
                self.tick = 0
            self.ymov -= d_tick * tickheight
            self.refresh()
        elif self.force_refresh:
            self.refresh()
            self.force_refresh = False
        for child in self.children:
            x = self.branch_x(child.branch)
            y = self.tick_y(child.tick_to)
            height = self.tick_y(child.tick_from) - y
            hs = self.spacing_y
            ws = self.spacing_x
            child.pos = (x + ws, y + hs)
            child.size = (branchwidth - ws, height - hs)

    def on_touch_down(self, touch):
        """Catch the touch if it hits me."""
        if self.collide_point(touch.x, touch.y):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        """Snap to the nearest branch and tick."""
        touch.grab_current = None
        self.xmov = 0
        self.xcess = 0
        self.ymov = 0
        self.ycess = 0
        self._trigger_layout()

    def on_touch_move(self, touch):
        """If I'm being dragged, trigger a layout, but first check to see if
I've been dragged far enough that I'm no longer at the same branch and
tick. If so, adjust my branch and tick to fit."""
        if touch.grab_current is self:
            if self.xcess == 0:
                nuxmov = self.xmov + touch.dx
                if not (self.branch == 0 and nuxmov < 0):
                    self.xmov = nuxmov
                else:
                    self.xcess += touch.dx
            else:
                self.xcess += touch.dx
                if self.xcess < 0:
                    self.xcess = 0
            if self.ycess == 0:
                nuymov = self.ymov + touch.dy
                if not (self.tick == 0 and nuymov < 0):
                    self.ymov = nuymov
                else:
                    self.ycess += touch.dy
            else:
                self.ycess += touch.dy
                if self.ycess > 0:
                    self.ycess = 0
            self._trigger_layout()


class CalendarLayout(RelativeLayout):
    """Really just a RelativeLayout with some Kivy properties to handle
the parameters of a Calendar."""
    character = ObjectProperty()
    item_type = NumericProperty()
    keys = ListProperty()
    edbut = ObjectProperty()
