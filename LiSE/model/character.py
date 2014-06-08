# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from networkx import DiGraph
from networkx import shortest_path as sp
from LiSE.orm import SaveableMetaclass
from thing import Thing
from place import Place
from portal import Portal


class AbstractCharacter(object):
    """Basis for classes implementing the Character API.

    The Character API is a graph structure built to reflect the state
    of its corner of the game world at the present time. Places and
    Portals are nodes and edges in this graph. Their stats and
    contents are accessible here as well.

    """
    __metaclass__ = SaveableMetaclass

    def __getitem__(self, key):
        return self.graph.graph[key]

    @property
    def graph(self):
        return self.get_graph()

    def get_graph(self):
        # It seems generally inefficient to regenerate the graph
        # whenever I look at it.
        #
        # It's the most convenient way, given I want the graph to
        # always reflect the current state of the world, regardless of
        # when I last looked at it. But perhaps I could do better,
        # later, by either:
        #
        # 1. subclassing DiGraph so that its node and edge attributes
        # are custom Mapping implementations that "contain" whatever's
        # current, or
        #
        # 2. caching the graph, and only regenerating it when the
        # world's been edited or the time cursor has moved.
        #
        # These approaches may even be compatible.
        return self.make_graph()

    def make_graph(self):
        """Generate and return a DiGraph representing all the Places,
        Portals, and Things in me.

        To find what's in me, I iterate over
        ``self.current_bones()``. Anything not yielded by that method
        doesn't go in the graph.

        """
        self.thing_contents_d = {}
        self.thing_stat_d = {}
        r = DiGraph()

        def cast(b):
            if b.type == 'text':
                return b.value
            elif b.type == 'real':
                return float(b.value)
            elif b.type == 'boolean':
                return bool(b.value)
            elif b.type == 'integer':
                return int(b.value)
            else:
                raise TypeError("Unsupported stat type: {}".format(b.type))

        def add_place(name):
            if name not in self.place_d:
                self.place_d[name] = Place(self, name)
            place = self.place_d[name]
            if name not in r.node:
                r.add_node(
                    name,
                    {
                        "place": place,
                        "contents": set()
                    }
                )
            return place

        def add_portal(origin, destination):
            add_place(origin)
            add_place(destination)
            if origin not in self.portal_d:
                self.portal_d = {}
            if destination not in self.portal_d[origin]:
                self.portal_d[origin][destination] = Portal(
                    self, origin, destination)
            portal = self.portal_d[origin][destination]
            if destination not in r.edge[origin]:
                r.add_edge(
                    origin,
                    destination,
                    {
                        "portal": portal,
                        "contents": set()
                    }
                )
            return portal

        def add_thing(name):
            if name not in self.thing_d:
                self.thing_d[name] = Thing(self, name)
            return self.thing_d[name]

        def process_portal_stat_bone(b):
            add_portal(b.origin, b.destination)
            r.edge[b.origin][b.destination][b.key] = cast(b)

        things2b = {}

        def process_thing_stat_bone(b):
            thing = add_thing(b.name)
            if b.key == 'location':
                if '->' in b.value:
                    (origin, destination) = b.value.split('->')
                    r.edge[origin][destination]["contents"].add(thing)
                else:
                    if b.value in r.node:
                        r.node[b.value]["contents"].add(thing)
                    else:
                        things2b[b.name] = b.value
            else:
                if b.name not in self.thing_stat_d:
                    self.thing_stat_d[b.name] = {}
                self.thing_stat_d[b.name][b.key] = cast(b)

        def postprocess_things():
            for thingn in things2b:
                thing = self.thing_d[thingn]
                if things2b[thingn] in things2b:
                    locn = things2b[thingn]
                    if locn not in self.thing_contents_d:
                        self.thing_contents_d[locn] = set()
                    self.thing_contents_d[locn].add(thing)
                elif thingn in r.node:
                    r.node[locn].contents.add(thing)
                else:
                    r.add_node(
                        locn,
                        {
                            "place": add_place(locn),
                            "contents": set([thing])
                        }
                    )

        def process_place_stat_bone(b):
            add_place(b.name)
            r.node[b.name][b.key] = cast(b)

        def process_character_stat_bone(b):
            r.graph[b.key] = cast(b)

        def shortest_path(o, d, weight=''):
            return sp(r, o, d, weight)
        shortest_path.__doc__ = sp.__doc__
        r.shortest_path = shortest_path

        for bone in self.current_bones():
            if isinstance(bone, Place.bonetype):
                process_place_stat_bone(bone)
            elif isinstance(bone, Portal.bonetype):
                process_portal_stat_bone(bone)
            elif isinstance(bone, Thing.bonetype):
                process_thing_stat_bone(bone)
            elif isinstance(bone, Character.bonetypes["character_stat"]):
                process_character_stat_bone(bone)
            else:
                raise TypeError("Unknown bonetype")
        postprocess_things()
        return r

    def transport_thing_to(self, thingn, destn, graph_for_pathfinding=None):
        """Set the thing to travel along the shortest path to the destination.

        It will spend however long it must in each of the places and
        portals along the path.

        With optional argument graph_for_pathfinding, it will try to
        follow the shortest path it can find in the given graph--which
        might cause it to stop moving earlier than expected, if the
        path it finds doesn't exist within me.

        """
        movegraph = self.graph
        pathgraph = (
            graph_for_pathfinding
            if graph_for_pathfinding else movegraph
        )
        o = self.thing_loc_d[thingn]
        path_sl = pathgraph.shortest_path(o, destn)
        placens = iter(path_sl)
        placen = next(placens)
        path_ports = []
        for placenxt in placens:
            try:
                path_ports.append(movegraph[placen][placenxt]['portal'])
                placen = placenxt
            except KeyError:
                break
        self.thing_d[thingn].follow_path(path_ports)

    def current_bones(self):
        raise NotImplementedError("Abstract class")


class Character(AbstractCharacter):
    """A part of the world model, comprising a graph, things in the graph,
    and stats of items in the graph.

    A Character instance's ``graph`` attribute will always give a
    representation of the character's state at the present
    sim-time.

    """
    provides = ["character"]
    tables = [
        (
            "character_stat",
            {
                "columns":
                {
                    "character": "text not null",
                    "key": "text not null",
                    "branch": "integer not null default 0",
                    "tick": "integer not null default 0",
                    "value": "text"
                },
                "primary_key":
                ("character", "key", "branch", "tick")
            }
        ),
        (
            "character_avatar",
            {
                "columns":
                {
                    "character": "text not null",
                    "host": "text not null default 'Physical'",
                    "type": "text not null default 'thing'",
                    "name": "text not null"
                },
                "primary_key":
                ("character", "host", "type", "name"),
                "checks":
                ["type in ('thing', 'place', 'portal')"]
            }
        )
    ]

    def __init__(self, closet, name):
        self.closet = closet
        self.name = name
        self.thing_d = {}
        self.thing_loc_d = {}
        self.thing_contents_d = {}
        self.thing_stat_d = {}
        self.place_d = {}
        self.portal_d = {}

    def __eq__(self, other):
        """Compare based on the name and the closet"""
        return (
            hasattr(other, 'name') and
            hasattr(other, 'closet') and
            self.closet is other.closet and
            self.name == other.name
        )

    def __hash__(self):
        """Hash of the name"""
        return hash(self.name)

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return unicode(self.name)

    def current_bones(self):
        (branch, tick) = self.closet.timestream.time
        skel = self.closet.skeleton
        thingskel = skel[u'thing_stat'][self.name]
        placeskel = skel[u'place_stat'][self.name]
        portalskel = skel[u'portal_stat'][self.name]
        charskel = skel[u'character_stat'][self.name]
        # TODO: more efficient iteration?
        for thing in thingskel:
            for key in thingskel[thing]:
                if branch in thingskel[thing][key]:
                    yield thingskel[thing][key][branch].value_during(tick)
        for place in placeskel:
            for key in placeskel[place]:
                if branch in placeskel[place][key]:
                    yield placeskel[place][key][branch].value_during(tick)
        for origin in portalskel:
            for destination in portalskel[origin]:
                for key in portalskel[origin][destination]:
                    if branch in portalskel[origin][destination][key]:
                        yield portalskel[origin][destination][
                            key][branch].value_during(tick)
        for key in charskel:
            if branch in charskel[key]:
                yield charskel[key][branch].value_during(tick)


class Facade(AbstractCharacter):
    """View onto one Character as seen by another.

    When Characters represent people, they will often want to know
    something, but be limited in their ability to get the information
    they want--perhaps because they are not in the right place to see
    what they are looking for, perhaps because their eyesight isn't
    good enough, or perhaps because the information in question
    requires a judgment call that a different person might make
    differently. Facade is used to model any such situation.

    An instance of Facade represents the combined collective opinions
    that one Character, the observer, has about another Character, the
    observed. By default, the observer sees all of the bones that are
    in the observed, sees them exactly as they really are, and doesn't
    see anything else. To change these assumptions, use the decorators
    ``distorter`` and ``fabricator`` on the Facade.

    """
    tables = [
        (
            "distorters",
            {
                "columns":
                {
                    "observer": "text not null",
                    "observed": "text not null",
                    "idx": "integer not null",
                    "branch": "integer not null",
                    "tick": "integer not null",
                    "function": "text"  # I'll just skip over any nulls
                },
                "primary_key":
                ("observer", "observed", "idx", "branch", "tick")
            }
        ),
        (
            "fabricators",
            {
                "columns":
                {
                    "observer": "text not null",
                    "observed": "text not null",
                    "idx": "integer not null",
                    "branch": "integer not null",
                    "tick": "integer not null",
                    "function": "text"
                },
                "primary_key":
                ("observer", "observed", "idx", "branch", "tick")
            }
        )
    ]

    def __init__(self, observer, observed):
        self.observer = observer
        self.observed = observed
        self.closet = self.observed.closet
        self.thing_d = {}
        self.thing_loc_d = {}
        self.thing_contents_d = {}
        self.thing_stat_d = {}
        self.place_d = {}
        self.portal_d = {}

    def __eq__(self, other):
        return (
            hasattr(other, 'observer') and
            hasattr(other, 'observed') and
            self.observer == other.observer and
            self.observed == other.observed)

    def __hash__(self):
        return hash((self.observer, self.observed))

    def __unicode__(self):
        return u"Facade({},{})".format(self.observer, self.observed)

    def _decorated_function_names(self, table):
        def get_function_name(skel, branch, tick):
            if branch not in skel:
                if branch == 0:
                    return None
                return get_function_name(
                    skel,
                    branch-1,
                    tick
                )
            return skel[branch].value_during(tick).function

        skel = (
            self.closet.skeleton
            [table]
            [self.observer.name]
            [self.observed.name]
        )
        (branch, tick) = self.closet.timestream.time
        for idx in skel:
            r = get_function_name(
                skel[idx],
                branch,
                tick
            )
            if r:
                yield r

    def _decorated_functions(self, table):
        for name in self._decorated_function_names(table):
            yield self.closet.shelf[name]

    def _distfab(self, table, fun, i=None):
        if i is not None and i < 0:
            raise ValueError("No negative indices")
        if isinstance(fun, str) or isinstance(fun, unicode):
            fun = self.closet.shelf[fun]
        elif fun.__name__ not in self.closet.shelf:
            self.closet.shelf[fun.__name__] = fun
        # TODO: if there's already a function in the shelf by the same
        # name, make sure it is the same as the function provided --
        # but don't use ``is`` because it might have been both loaded
        # in from the shelf and also declared in the running code.
        #
        # Perhaps pickle the given function and compare that to what's
        # in the shelf
        if self.observer.name not in self.closet.skeleton[table]:
            self.closet.skeleton[table][self.observer.name] = {}
        skel = self.closet.skeleton[table][self.observer.name]
        if self.observed.name not in skel:
            skel[self.observed.name] = {}
        skel = skel[self.observed.name]
        if i is None:
            try:
                i = max(skel.viewkeys()) + 1
            except ValueError:
                i = 0
        (branch, tick) = self.closet.timestream.time
        self.closet.set_bone(
            self.bonetypes[table](
                observer=self.observer.name,
                observed=self.observed.name,
                idx=i,
                branch=branch,
                tick=tick,
                function=fun.__name__
            )
        )

    def _rm_distfab(self, table, fun):
        if not (isinstance(fun, str) or isinstance(fun, unicode)):
            fun = fun.__name__
        skel = (
            self.closet.skeleton
            [table]
            [self.observer.name]
            [self.observed.name]
        )
        (branch, tick) = self.closet.timestream.time
        for idx in skel:
            bone = skel[idx][branch].value_during(tick)
            if bone.function == fun:
                self.closet.set_bone(
                    self.bonetypes[table](
                        observer=self.observer.name,
                        observed=self.observed.name,
                        idx=idx,
                        branch=branch,
                        tick=tick,
                        function=fun
                    )
                )

    def distorter(self, fun, i=None):
        """Decorate a distorter function that takes this Facade and one bone
        from the observed character, and returns another bone of the
        same class, possibly identical to the input, but possibly
        distorted, and possibly None to indicate that the bone should
        be omitted altogether.

        It is also permissible to decorate a generator that yields
        several bones in turn.

        Bones will be passed through each distorter function in turn
        before being used to build the graph. If your function should
        only distort some bones some of the time, have it return the
        rest of the bones untouched, the rest of the time.

        Optional argument ``i`` will be the index of the distorter in
        the sequence. Must be non-negative if provided.

        You may supply a string instead of a function, in which case a
        previously decorated function of the given name will be used.

        """
        return self._distfab("distorters", fun, i)

    def remove_distorter(self, fun):
        return self._rm_distfab("distorters", fun)

    def distorters(self):
        for fun in self._decorated_functions("distorters"):
            yield fun

    def distort(self, bone):
        bonecls = bone.__class__
        for fun in self.distorters():
            r = fun(self, bone)
            if hasattr(r, 'next'):
                it = r
            else:
                it = iter([r])
            for bone in it:
                if bone is None:
                    return
                if not isinstance(bone, bonecls):
                    raise TypeError(
                        "Distorter {} returned bone of class {}"
                        " (expected {})".format(
                            fun.__name__,
                            bone.__class__.__name__,
                            bonecls.__name__
                        )
                    )
                yield bone

    def distortions(self):
        for bone in self.observed.current_bones():
            r = self.distort(bone)
            for b in r:
                yield b

    def fabricator(self, fun, i=None):
        """Decorate a fabricator function that takes this Facade and returns
        one bone, which will be reported as being in the observed
        character, though in fact it is not.

        It is also permissible to decorate a generator that yields
        several bones in turn.

        Optional argument ``i`` will be the index of the fabricator in
        the sequence. Must be non-negative if provided.

        You may supply a string instead of a function, in which case a
        previously decorated function of the given name will be used.

        The fabricator will apply to this Facade on all ticks after
        the present, in this branch and those descended from it,
        unless removed with the ``remove_fabricator`` method or by
        overwriting it with ``None``.

        """
        return self._distfab("fabricators", fun, i)

    def remove_fabricator(self, fun):
        """Stop using the fabricator after the present tick.

        If the same fabricator has been decorated more than once, this
        removes them all.

        """
        return self._rm_distfab("fabricators", fun)

    def fabricators(self):
        for fun in self._decorated_functions("fabricators"):
            yield fun

    def fabrications(self):
        for fun in self.fabricators:
            r = fun(self)
            if hasattr(r, 'next'):
                for fab in r:
                    yield fab
            else:
                yield r

    def current_bones(self):
        for fabrication in self.fabrications:
            yield fabrication
        for distortion in self.distortions:
            yield distortion
