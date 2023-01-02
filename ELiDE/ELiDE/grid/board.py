from collections import defaultdict
from functools import partial

from kivy.clock import Clock
from kivy.logger import Logger
from kivy.properties import (DictProperty, ListProperty, NumericProperty,
								ObjectProperty, ReferenceListProperty)
from kivy.uix.widget import Widget
from kivy.lang.builder import Builder
from .spot import GridSpot
from .pawn import GridPawn
from ..boardview import BoardView
from ..pawnspot import TextureStackPlane


class GridBoard(Widget):
	selection = ObjectProperty()
	selection_candidates = ListProperty()
	character = ObjectProperty()
	tile_width = NumericProperty(32)
	tile_height = NumericProperty(32)
	tile_size = ReferenceListProperty(tile_width, tile_height)

	def __init__(self, **kwargs):
		self.pawn = {}
		self.spot = {}
		self.contained = defaultdict(set)
		super().__init__(**kwargs)

	def add_spot(self, placen, *args):
		if placen not in self.character.place:
			raise KeyError(f"No such place for spot: {placen}")
		self._spot_plane.add_datum(self.make_spot(
			self.character.place[placen]))

	def make_spot(self, place):
		placen = place["name"]
		if not isinstance(placen, tuple) or len(placen) != 2:
			raise TypeError(
				"Can only make spot from places with tuple names of length 2")
		if placen in self.spot:
			raise KeyError("Already have a Spot for this Place")
		if not isinstance(placen, tuple) or len(placen) != 2 or not isinstance(
			placen[0], int) or not isinstance(placen[1], int):
			raise TypeError(
				"GridBoard can only display places named with pairs of ints")
		if "_image_paths" in place:
			textures = list(place["_image_paths"])
		else:
			textures = list(GridPawn.default_image_paths)
		r = {
			"name": placen,
			"x": placen[0] * int(self.tile_width),
			"y": placen[1] * int(self.tile_height),
			"width": self.tile_width,
			"height": self.tile_height,
			"textures": textures,
		}
		self.spot[place["name"]] = r
		return r

	def make_pawn(self, thing) -> dict:
		if thing["name"] in self.pawn:
			raise KeyError("Already have a Pawn for this Thing")
		location = self.spot[thing["location"]]
		r = {
			"name": thing["name"],
			"x": location["x"],
			"y": location["y"],
			"width": self.tile_width,
			"height": self.tile_height,
			"location": location,
			"textures": list(thing["_image_paths"])
		}
		self.pawn[thing["name"]] = r
		return r

	def add_pawn(self, thingn, *args):
		if thingn not in self.character.thing:
			raise KeyError(f"No such thing: {thingn}")
		if thingn in self.pawn:
			raise KeyError(f"Already have a pawn for {thingn}")
		pwn = self.make_pawn(self.character.thing[thingn])
		location = pwn['location']
		self.contained[location].add(thingn)
		self._pawn_plane.add_datum(pwn)

	def _trigger_add_pawn(self, thingn):
		part = partial(self.add_pawn, thingn)
		Clock.unschedule(part)
		Clock.schedule_once(part, 0)

	def on_parent(self, *args):
		if not self.character:
			Clock.schedule_once(self.on_parent, 0)
			return
		if not hasattr(self, '_pawn_plane'):
			self._pawn_plane = TextureStackPlane(pos=self.pos, size=self.size)
			self._spot_plane = TextureStackPlane(pos=self.pos, size=self.size)
			self.bind(pos=self._pawn_plane.setter('pos'),
						size=self._pawn_plane.setter('size'))
			self.bind(pos=self._spot_plane.setter('pos'),
						size=self._spot_plane.setter('size'))
			self.add_widget(self._spot_plane)
			self.add_widget(self._pawn_plane)
		spot_data = list(map(self.make_spot, self.character.place.values()))
		wide = max(datum["x"] for datum in spot_data) + self.tile_width
		high = max(datum["y"] for datum in spot_data) + self.tile_width
		self.size = self._spot_plane.size = self._pawn_plane.size = wide, high
		pawn_data = list(map(self.make_pawn, self.character.thing.values()))
		self._spot_plane.data = spot_data
		self._pawn_plane.data = pawn_data

	def rm_spot(self, name):
		spot = self.spot.pop(name)
		if spot in self.selection_candidates:
			self.selection_candidates.remove(spot)
		for pwn in spot.children:
			del self.pawn[pwn.name]
		self._spot_plane.remove_datum(spot)

	def rm_pawn(self, name):
		pwn = self.pawn.pop(name)
		if pwn in self.selection_candidates:
			self.selection_candidates.remove(pwn)
		self._pawn_plane.remove_datum(pwn)

	def update_from_delta(self, delta, *args):
		pawnmap = self.pawn
		spotmap = self.spot
		add_pawn = self.add_pawn
		add_spot = self.add_spot
		selection_candidates = self.selection_candidates

		def rm_pawn(name):
			pwn = pawnmap.pop(name)
			if pwn in selection_candidates:
				selection_candidates.remove(pwn)
			self._pawn_plane.remove_datum(pwn)

		def rm_spot(name):
			spot = spotmap.pop(name)
			if spot in selection_candidates:
				selection_candidates.remove(spot)
			for pwn in self.contained[name]:
				del pawnmap[pwn.name]
			del self.contained[name]
			self._spot_plane.remove_datum(spot)

		if 'nodes' in delta:
			for node, extant in delta['nodes'].items():
				if extant:
					if 'node_val' in delta and node in delta[
						'node_val'] and 'location' in delta['node_val'][
							node] and node not in pawnmap:
						add_pawn(node)
					elif node not in spotmap:
						add_spot(node)
				else:
					if node in pawnmap:
						rm_pawn(node)
					if node in spotmap:
						rm_spot(node)
		if 'node_val' in delta:
			for node, stats in delta['node_val'].items():
				if node in spotmap and '_image_paths' in stats:
					spotmap[node].paths = stats[
						'_image_paths'] or GridSpot.default_image_paths
				elif node in pawnmap:
					pawn = pawnmap[node]
					if 'location' in stats:
						pawn.loc_name = stats['location']
					if '_image_paths' in stats:
						pawn.paths = stats[
							'_image_paths'] or GridPawn.default_image_paths
				else:
					Logger.warning(
						"GridBoard: diff tried to change stats of node {}"
						"but I don't have a widget for it".format(node))

	def trigger_update_from_delta(self, delta, *args):
		part = partial(self.update_from_delta, delta)
		Clock.unschedule(part)
		Clock.schedule_once(part, 0)


class GridBoardView(BoardView):
	pass


Builder.load_string("""
<GridBoard>:
	app: app
	size_hint: None, None
<GridBoardView>:
	plane: boardplane
	BoardScatterPlane:
		id: boardplane
		board: root.board
		scale_min: root.scale_min
		scale_max: root.scale_max
""")
