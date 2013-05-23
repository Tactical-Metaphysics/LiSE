from util import (
    SaveableMetaclass,
    dictify_row,
    stringlike)
from event import (
    lookup_between,
    Event,
    SenselessEvent,
    ImpossibleEvent,
    IrrelevantEvent,
    ImpracticalEvent,
    PortalTravelEvent)
from effect import Effect, EffectDeck
import re


__metaclass__ = SaveableMetaclass


class Item:
    tables = [
        ("item",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]

    def __str__(self):
        return self.name


class Place(Item):
    tables = [
        ("place",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, dimension, name, db):
        self.dimension = dimension
        self.name = name
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if dimname not in db.itemdict:
                db.itemdict[dimname] = {}
            if dimname not in db.placedict:
                db.placedict[dimname] = {}
            db.itemdict[dimname][self.name] = self
            db.placedict[dimname][self.name] = self

    def unravel(self, db):
        """Get myself a real Dimension object if I don't have one."""
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if not hasattr(self, 'contents'):
            if self.dimension.name not in db.contentsdict:
                db.contentsdict[self.dimension.name] = {}
            if self.name not in db.contentsdict[self.dimension.name]:
                db.contentsdict[self.dimension.name][self.name] = set()
            self.contents = db.contentsdict[self.dimension.name][self.name]

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def add(self, other):
        self.contents.add(other)

    def remove(self, other):
        self.contents.remove(other)

    def can_contain(self, other):
        """Does it make sense for that to be here?"""
        return True


class Portal(Item):
    tables = [
        ("portal",
         {"dimension": "text",
          "name": "text",
          "from_place": "text",
          "to_place": "text"},
         ("dimension", "name"),
         {"dimension, name": ("item", "dimension, name"),
          "dimension, from_place": ("place", "dimension, name"),
          "dimension, to_place": ("place", "dimension, name")},
         [])]

    def __init__(self, dimension, name, from_place, to_place, db=None):
        self.dimension = dimension
        self.name = name
        self.orig = from_place
        self.dest = to_place
        if db is not None:
            dimname = None
            from_place_name = None
            to_place_name = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if stringlike(self.orig):
                from_place_name = self.orig
            else:
                from_place_name = self.orig.name
            if stringlike(self.dest):
                to_place_name = self.dest
            else:
                to_place_name = self.dest.name
            podd = db.portalorigdestdict
            pdod = db.portaldestorigdict
            for d in [db.itemdict, db.portaldict, podd, pdod]:
                if dimname not in d:
                    d[dimname] = {}
            if from_place_name not in podd[dimname]:
                podd[dimname][from_place_name] = {}
            if to_place_name not in pdod[dimname]:
                pdod[dimname][to_place_name] = {}
            db.itemdict[dimname][self.name] = self
            db.portaldict[dimname][self.name] = self
            podd[dimname][from_place_name][to_place_name] = self
            pdod[dimname][to_place_name][from_place_name] = self

    def unravel(self, db):
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.orig):
            self.orig = db.itemdict[self.dimension.name][self.orig]
        if stringlike(self.dest):
            self.dest = db.itemdict[self.dimension.name][self.dest]

    def __hash__(self):
        return self.hsh

    def get_weight(self):
        return self.weight

    def get_avatar(self):
        return self.avatar

    def is_passable_now(self):
        return True

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def is_now_passable_by(self, traveler):
        return self.isPassableNow() and self.admits(traveler)

    def get_dest(self):
        return self.dest

    def get_orig(self):
        return self.orig

    def get_ends(self):
        return [self.orig, self.dest]

    def touches(self, place):
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals

    def notify_moving(self, thing, amount):
        """Handler for when a thing moves through me by some amount of my
length. Does nothing by default."""
        pass

    def add(self, thing):
        """Add this thing to my contents if it's not there already."""
        self.contents.add(thing)

    def remove(self, thing):
        """Remove this thing from my contents."""
        self.contents.remove(thing)


class Thing(Item):
    tables = [
        ("thing",
         {"dimension": "text",
          "name": "text",
          "location": "text not null",
          "journey_progress": "float default 0.0",
          "journey_step": "integer default 0",
          "age": "integer default 0"},
         ("dimension", "name"),
         {"dimension, location": ("item", "dimension, name")},
         [])]

    def __init__(self, dimension, name, location,
                 journey_step=0, journey_progress=0.0, age=0,
                 schedule=None, db=None):
        """Return a Thing in the given dimension and location,
with the given name. Its contents will be empty to start; later on,
point some other Things' location attributes at this Thing to put
them in.

Register with the database's itemdict and thingdict too.

        """
        self.dimension = dimension
        self.name = name
        self.starting_location = location
        self.journey_step = journey_step
        self.journey_progress = journey_progress
        self.age = age
        self.schedule = schedule
        self.hsh = hash(hash(self.dimension) + hash(self.name))
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if dimname not in db.itemdict:
                db.itemdict[dimname] = {}
            if dimname not in db.thingdict:
                db.thingdict[dimname] = {}
            if dimname not in db.locdict:
                db.locdict[dimname] = {}
            db.itemdict[dimname][self.name] = self
            db.thingdict[dimname][self.name] = self
            db.locdict[dimname][self.name] = location

    def unravel(self, db):
        """Dereference stringlike attributes.

Also add self to location, if applicable.

        """
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.start_location):
            locn = self.start_location
            location = db.itemdict[self.dimension.name][locn]
        else:
            location = self.start_location
        db.locdict[self.dimension.name][self.name] = location
        self.location = Location(db, self.dimension.name, self.name)
        if self.dimension.name not in db.contentsdict:
            db.contentsdict[self.dimension.name] = {}
        if self.name not in db.contentsdict[self.dimension.name]:
            db.contentsdict[self.dimension.name][self.name] = set()
        self.contents = db.contentsdict(self.dimension.name, self.name)
        if stringlike(self.schedule):
            self.schedule = db.scheduledict[self.dimension.name][self.name]
            self.schedule.unravel(db)
        if (
                self.dimension.name in db.journeydict and
                self.name in db.journeydict[self.dimension.name]):
            self.journey = db.journeydict[self.dimension.name][self.name]
            self.journey.unravel(db)
            if self.schedule is None:
                self.schedule = self.journey.schedule(db)
                self.schedule.unravel(db)

    def __hash__(self):
        return self.hsh

    def __str__(self):
        return "(%s, %s)" % (self.dimension, self.name)

    def __iter__(self):
        return (self.dimension, self.name)

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

    def add(self, it):
        """Add an item to my contents without caring if it makes any sense to
do so.

This will not, for instance, remove the item from wherever it currently is.

"""
        self.contents.add(it)

    def remove(self, it):
        """Remove an item from my contents without putting it anywhere else.

The item might end up not being contained in anything, leaving it
inaccessible. Beware.

"""
        self.contents.remove(it)

    def can_enter(self, it):
        """If I can't enter the given location, raise a LocationException.

Assume that the given location has no objections."""
        pass

    def can_leave_location(self):
        """If I can't leave the location I'm currently in, raise a
LocationException."""
        return True

    def can_contain(self, it):
        """If I can't contain the given item, raise a ContainmentException."""
        return True

    def enter(self, it):
        """Check if I can go into the destination, and if so, do it
immediately. Else raise exception as appropriate."""
        self.can_leave_location()
        self.can_enter(it)
        it.can_contain(self)
        self.location.remove(self)
        it.add(self)

    def move_thru_portal(self, amount):
        """Move this amount through the portal I'm in"""
        self.location.notify_moving(self, amount)
        self.journey_progress += amount

    def leave_portal(self):
        """Leave whatever portal I'm in, thus entering its destination."""
        self.enter(self.location.dest)

    def speed_thru(self, port):
        """Given a portal, return an integer for the number of ticks it would
take me to pass through it."""
        return 60


class Journey:
    """Series of steps taken by a Thing to get to a Place.

    Journey is the class for keeping track of a path that a traveller
    wants to take across one of the game maps. It is stateful: it
    tracks where the traveller is, and how far it's gotten along the
    edge through which it's travelling. Each step of the journey is a
    portal in the steps supplied on creation. The list should consist
    of Portals in the precise order that they are to be travelled
    through.

    Each Journey has a progress attribute. It is a float, at least 0.0
    and less than 1.0. When the traveller moves some distance along
    the current Portal, call move(prop), where prop is a float, of the
    same kind as progress, representing the proportion of the length
    of the Portal that the traveller has travelled. progress will be
    updated, and if it meets or exceeds 1.0, the current Portal will
    become the previous Portal, and the next Portal will become the
    current Portal. progress will then be decremented by 1.0.

    You probably shouldn't move the traveller through more than 1.0 of
    a Portal at a time, but Journey handles that case anyhow.

    """
    tables = [
        ("journey_step",
         {"dimension": "text",
          "thing": "text",
          "idx": "integer",
          "portal": "text"},
         ("dimension", "thing", "idx"),
         {"dimension, thing": ("thing", "dimension, name"),
          "dimension, portal": ("portal", "dimension, name")},
         [])]

    def __init__(self, dimension, thing, steps, db=None):
        self.dimension = dimension
        self.thing = thing
        self.steps = steps
        if db is not None:
            dimname = None
            thingname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if stringlike(self.thing):
                thingname = self.thing
            else:
                thingname = self.thing.name
            if dimname not in db.journeydict:
                db.journeydict[dimname] = {}
            db.journeydict[dimname][thingname] = self

    def unravel(self, db):
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.thing):
            self.thing = db.itemdict[self.dimension.name][self.thing]
        i = 0
        while i < len(self.steps):
            if stringlike(self.steps[i]):
                self.steps[i] = (
                    db.portaldict[self.dimension.name][self.steps[i]])
            i += 1

    def __len__(self):
        """Get the number of steps in the Journey.

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)

    def steps_left(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps) - self.thing.journey_step

    def __getitem__(self, i):
        """Get the ith next Portal in the journey.

        __getitem__(0) returns the portal the traveller is presently
        travelling through. __getitem__(1) returns the one it wil travel
        through after that, etc. __getitem__(-1) returns the step before
        this one, __getitem__(-2) the one before that, etc.

        If i is out of range, returns None.

        """
        return self.steps[i+self.thing.journey_step]

    def speed_at_step(self, i):
        """Get the thing's speed at step i.

Speed is the proportion of the portal that the thing passes through
per unit of game time. It is expressed as a float, greater than zero,
no greater than one.

Speed should be expected to vary a lot depending on the properties and
current status of the thing and the portal. Thus it is delegated to a
method of the thing that operates on the portal.

"""
        return self.thing.speed_thru(self.getstep(i))

    def move_thru_portal(self, prop):
        """Move the thing the specified amount through the current
portal. Return the updated progress.

*Don't* move the thing *out* of the portal. Raise a PortalException if
the thing isn't in a portal at all.

        """
        return self.thing.move_thru_portal(prop)

    def next(self):
        """Teleport the thing to the destination of the portal it's in, and
advance the journey.

Return a pair containing the new place and the new portal. If the
place is the destination of the journey, the new portal will be
None.

        """
        oldport = self.thing.leave_portal()
        place = self.thing.enter_place(oldport.dest)
        self.thing.journey_step += 1
        self.thing.journey_progress = 0.0
        try:
            newport = self.get_step()
        except IndexError:
            newport = None
        return (place, newport)

    def __setitem__(self, idx, port):
        """Put given portal into the steplist at given index, padding steplist
with None as needed."""
        while idx >= len(self.steplist):
            self.steplist.append(None)
        self.steplist[idx] = port

    def schedule(self, db, delay=0):
        """Add events representing this journey to the very end of the thing's
schedule, if it has one.

Optional argument delay adds some ticks of inaction between the end of
the schedule and the beginning of the journey. If there's no schedule,
or an empty one, that's the amount of time from the start of the game
that the thing will wait before starting the journey.

Then return the schedule. Just for good measure.

        """
        if not hasattr(self.thing, 'schedule'):
            self.thing.schedule = Schedule(self.thing.dimension, self.thing, db)
        try:
            end = max(self.thing.schedule.events_ending.viewkeys())
        except ValueError:
            end = 0
        start = end + delay
        for port in self.steplist:
            newev = PortalTravelEvent(self.thing, port, False, db)
            evlen = self.thing.speed_thru(port)
            self.thing.schedule.add(newev.scheduled_copy(start, evlen))
            start += evlen
        return self.thing.schedule


class Schedule:
    tables = [
        ("scheduled_event",
         {"dimension": "text",
          "item": "text",
          "start": "integer",
          "event": "text not null",
          "length": "integer"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "event": ("event", "name")},
         [])]

    def __init__(self, dimension, item, db=None):
        self.dimension = dimension
        self.item = item
        self.events = {}
        self.events_starting = dict()
        self.events_ending = dict()
        self.events_ongoing = dict()
        self.cached_commencements = {}
        self.cached_processions = {}
        self.cached_conclusions = {}
        if db is not None:
            dimname = None
            itemname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if stringlike(self.item):
                itemname = self.item
            else:
                itemname = self.item.name
            if dimname not in db.scheduledict:
                db.scheduledict[dimname] = {}
            db.scheduledict[dimname][itemname] = self
            if dimname not in db.startevdict:
                db.startevdict[dimname] = {}
            db.startevdict[dimname][itemname] = self.events_starting
            if dimname not in db.contevdict:
                db.contevdict[dimname] = {}
            db.contevdict[dimname][itemname] = self.events_ongoing
            if dimname not in db.endevdict:
                db.endevdict[dimname] = {}
            db.endevdict[dimname][itemname] = self.events_ending

    def __iter__(self):
        return self.events.itervalues()

    def __len__(self):
        return max(self.events_ongoing.viewkeys())

    def unravel(self, db):
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.item):
            self.item = db.itemdict[self.dimension.name][self.item]
        self.add_global = db.add_event
        self.remove_global = db.remove_event
        self.discard_global = db.discard_event

    def trash_cache(self, start):
        for cache in [
                self.cached_commencements,
                self.cached_processions,
                self.cached_conclusions]:
            try:
                del cache[start]
            except KeyError:
                pass

    def add(self, ev):
        self.events[ev.name] = ev
        ev_end = ev.start + ev.length
        if ev.start not in self.events_starting:
            self.events_starting[ev.start] = set()
        if ev_end not in self.events_ending:
            self.events_ending[ev_end] = set()
        for i in xrange(ev.start+1, ev_end-1):
            if i not in self.events_ongoing:
                self.events_ongoing[i] = set()
            self.events_ongoing[i].add(ev)
        self.events_starting[ev.start].add(ev)
        self.events_ending[ev_end].add(ev)
        self.add_global(ev)
        self.trash_cache(ev.start)

    def remove(self, ev):
        """Remove an event from all my dictionaries."""
        del self.events[ev.name]
        ev_end = ev.start + ev.length
        self.events_starting[ev.start].remove(ev)
        for i in xrange(ev.start+1, ev_end-1):
            self.events_ongoing[i].remove(ev)
        self.events_ending[ev_end].remove(ev)

    def discard(self, ev):
        """Remove an event from all my dictionaries in which it is a
member."""
        del self.events[ev.name]
        if not hasattr(ev, 'start') or not hasattr(ev, 'length'):
            return
        ev_end = ev.start + ev.length
        self.events_starting[ev.start].discard(ev)
        self.events_ending[ev_end].discard(ev)
        for i in xrange(ev.start+1, ev_end-1):
            self.events_ongoing[i].discard(ev)
        self.discard_global(ev)
        self.trash_cache(ev.start)

    def commencements_between(self, start, end):
        if (
                start in self.cached_commencements and
                end in self.cached_commencements[start]):
            return self.cached_commencements[start][end]
        lookup = lookup_between(self.events_starting, start, end)
        if start not in self.cached_commencements:
            self.cached_commencements[start] = {}
        self.cached_commencements[start][end] = lookup
        return lookup

    def processions_between(self, start, end):
        if (
                start in self.cached_processions and
                end in self.cached_processions[start]):
            return self.cached_processions[start][end]
        lookup = lookup_between(self.events_ongoing, start, end)
        if start not in self.cached_processions:
            self.cached_processions[start] = {}
        self.cached_processions[start][end] = lookup
        return lookup

    def conclusions_between(self, start, end):
        if (
                start in self.cached_conclusions and
                end in self.cached_conclusions[start]):
            return self.cached_conclusions[start][end]
        lookup = lookup_between(self.events_ending, start, end)
        if start not in self.cached_conclusions:
            self.cached_conclusions[start] = {}
        self.cached_conclusions[start][end] = lookup
        return lookup

    def events_between(self, start, end):
        return (self.commencements_between(start, end),
                self.processions_between(start, end),
                self.conclusions_between(start, end))


def lookup_loc(db, it):
    """Return the item that the given one is inside, possibly None."""
    if stringlike(it.dimension):
        dimname = it.dimension
    else:
        dimname = it.dimension.name
    return db.locdict[dimname][it.name]


def make_loc_getter(db, it):
    """Return a function with no args that will always return the present
location of the item, possibly None."""
    return lambda: lookup_loc(db, it)


thing_dimension_qryfmt = (
    "SELECT {0} FROM thing WHERE dimension IN "
    "({1})".format(
        ", ".join(Thing.colns), "{0}"))


def read_things_in_dimensions(db, dimnames):
    qryfmt = thing_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Thing.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Thing(**rowdict)
    return r


def unravel_things(db, tdb):
    for thing in tdb.itervalues():
        thing.unravel(db)
    return tdb


def unravel_things_in_dimensions(db, tddb):
    for things in tddb.itervalues():
        unravel_things(db, things)
    return tddb


def load_things_in_dimensions(db, dimnames):
    return unravel_things_in_dimensions(
        db, read_things_in_dimensions(db, dimnames))


schedule_dimension_qryfmt = (
    "SELECT {0} FROM scheduled_event WHERE dimension IN "
    "({1})".format(
        ", ".join(Schedule.colnames["scheduled_event"]), "{0}"))


def read_schedules_in_dimensions(db, dimnames):
    qryfmt = schedule_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Item.colnames["scheduled_event"])
        if rowdict["item"] not in r[rowdict["dimension"]]:
            r[rowdict["dimension"]][rowdict["item"]] = {
                "db": db,
                "dimension": rowdict["dimension"],
                "item": rowdict["item"],
                "events": {}}
        rptr = r[rowdict["dimension"]][rowdict["item"]]
        rptr["events"][rowdict["start"]] = {
            "event": rptr["event"],
            "start": rptr["start"],
            "length": rptr["length"]}
    for level0 in r.iteritems():
        (dimn, its) = level0
        for it in its.iteritems():
            (itn, sched) = it
            r[dimn][itn] = Schedule(**sched)
    return r


def unravel_schedules(db, schd):
    for sched in schd.itervalues():
        sched.unravel(db)
    return schd


def unravel_schedules_in_dimensions(db, schdd):
    for scheds in schdd.itervalues():
        unravel_schedules(db, scheds)
    return schdd


def load_schedules_in_dimensions(db, dimnames):
    return unravel_schedules_in_dimensions(
        db, read_schedules_in_dimensions(db, dimnames))


journey_dimension_qryfmt = (
    "SELECT {0} FROM journey_step WHERE dimension IN "
    "({1})".format(
        ", ".join(Journey.colnames["journey_step"]), "{0}"))


def read_journeys_in_dimensions(db, dimnames):
    qryfmt = journey_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Journey.colnames["journey_step"])
        if rowdict["thing"] not in r[rowdict["dimension"]]:
            r[rowdict["dimension"]][rowdict["thing"]] = {
                "db": db,
                "dimension": rowdict["dimension"],
                "thing": rowdict["thing"],
                "steps": []}
        stepl = r[rowdict["dimension"]][rowdict["thing"]]["steps"]
        while len(stepl) <= rowdict["idx"]:
            stepl.append(None)
        stepl[rowdict["idx"]] = rowdict["portal"]
    for item in r.iteritems():
        (dimname, journeys) = item
        for journey in journeys.iteritems():
            (thingname, jo) = journey
            r[dimname][thingname] = Journey(**jo)
    return r


def unravel_journeys(db, jod):
    for jo in jod.itervalues():
        jo.unravel(db)
    return jod


def unravel_journeys_in_dimensions(db, jodd):
    for jod in jodd.itervalues():
        unravel_journeys(db, jod)
    return jodd


def load_journeys_in_dimensions(db, dimnames):
    return unravel_journeys_in_dimensions(
        db, read_journeys_in_dimensions(db, dimnames))


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


def read_places_in_dimensions(db, dimnames):
    qryfmt = place_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Place.colnames["place"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Place(**rowdict)
    return r


def unravel_places(db, pls):
    for pl in pls.itervalues():
        pl.unravel(db)
    return pls


def unravel_places_in_dimensions(db, pls):
    for pl in pls.itervalues():
        unravel_places(db, pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    return unravel_places_in_dimensions(
        db, load_places_in_dimensions(db, dimnames))



portal_colstr = ", ".join(Portal.colnames["portal"])
portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(portal_colstr, "{0}"))


def read_portals_in_dimensions(db, dimnames):
    qryfmt = portal_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Portal.colnames["portal"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Portal(**rowdict)
    return r


def unravel_portals(db, portd):
    for port in portd.itervalues():
        port.unravel(db)
    return portd


def unravel_portals_in_dimensions(db, portdd):
    for ports in portdd.itervalues():
        unravel_portals(db, ports)
    return portdd


def load_portals_in_dimensions(db, dimnames):
    return unravel_portals_in_dimensions(
        db, read_portals_in_dimensions(db, dimnames))
