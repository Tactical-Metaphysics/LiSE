# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) Zachary Spector, public@zacharyspector.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import networkx as nx
import pytest


@pytest.fixture(scope='function')
def something(engy):
    yield engy.new_character('physical').new_place('somewhere').new_thing('something')


def test_contents(something):
    pl1 = something.character.place['somewhere']
    pl2 = something.character.new_place('somewhere2')
    assert something.location == something.character.node['somewhere']
    assert something.name in pl1.content
    assert not something.name in pl2.content
    assert [something] == list(pl1.contents())
    assert [] == list(pl2.contents())


def test_travel(engy):
    phys = engy.new_character('physical')
    phys.copy_from(nx.grid_2d_graph(8, 8))
    del phys.place[1, 1]
    del phys.place[6, 1]
    thing1 = phys.place[0, 0].new_thing(1)
    thing2 = phys.place[7, 0].new_thing(2)
    thing1.travel_to(phys.place[7, 7])
    thing2.travel_to(phys.place[0, 7])
    engy.turn = 14
    assert thing1.location == phys.place[7, 7]
    assert thing2.location == phys.place[0, 7]
