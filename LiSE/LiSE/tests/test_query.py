# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) Zachary Spector, public@zacharyspector.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import re
from functools import reduce
from collections import defaultdict
from ..engine import Engine
from ..query import windows_intersection
import pytest
import os
import shutil
import tempfile

pytestmark = [pytest.mark.slow]


@pytest.fixture(scope='module')
def college24_premade():
	directory = tempfile.mkdtemp('.')
	shutil.unpack_archive(
		os.path.join(os.path.abspath(os.path.dirname(__file__)),
						'college24_premade.tar.xz'), directory)
	with Engine(directory) as eng:
		yield eng
	shutil.rmtree(directory)


def roommate_collisions(college24_premade):
	"""Test queries' ability to tell that all of the students that share
	rooms have been in the same place.

	"""
	engine = college24_premade
	done = set()
	for chara in engine.character.values():
		if chara.name in done:
			continue
		match = re.match(r'dorm(\d)room(\d)student(\d)', chara.name)
		if not match:
			continue
		dorm, room, student = match.groups()
		other_student = '1' if student == '0' else '0'
		student = chara
		other_student = engine.character['dorm{}room{}student{}'.format(
			dorm, room, other_student)]
		cond = student.unit.only.historical(
			'location') == other_student.unit.only.historical('location')
		same_loc_turns = {turn for (branch, turn) in cond._iter_times()}
		assert same_loc_turns, "{} and {} don't seem to share a room".format(
			student.name, other_student.name)
		assert len(
			same_loc_turns
		) >= 6, "{} and {} did not share their room for at least 6 turns".format(
			student.name, other_student.name)

		assert same_loc_turns == engine.turns_when(cond)

		done.add(student.name)
		done.add(other_student.name)


def test_roomie_collisions_premade(college24_premade):
	roommate_collisions(college24_premade)


def sober_collisions(college24_premade):
	"""Students that are neither lazy nor drunkards should all have been
	in class together at least once.

	"""
	engine = college24_premade
	students = [
		stu for stu in engine.character['student_body'].stat['characters']
		if not (stu.stat['drunkard'] or stu.stat['lazy'])
	]

	assert students

	def sameClasstime(stu0, stu1):
		assert list(
			engine.turns_when((stu0.unit.only.historical(
				'location') == stu1.unit.only.historical('location')) & (
					stu1.unit.only.historical('location') == 'classroom'))
		), """{stu0} seems not to have been in the classroom 
				at the same time as {stu1}.
				{stu0} was there at turns {turns0}
				{stu1} was there at turns {turns1}""".format(
			stu0=stu0.name,
			stu1=stu1.name,
			turns0=list(
				engine.turns_when(
					stu0.unit.only.historical('location') == 'classroom')),
			turns1=list(
				engine.turns_when(
					stu1.unit.only.historical('location') == 'classroom')))
		return stu1

	reduce(sameClasstime, students)


def test_sober_collisions_premade(college24_premade):
	sober_collisions(college24_premade)


def noncollision(college24_premade):
	"""Make sure students *not* from the same room never go there together"""
	engine = college24_premade
	dorm = defaultdict(lambda: defaultdict(dict))
	for character in engine.character.values():
		match = re.match(r'dorm(\d)room(\d)student(\d)', character.name)
		if not match:
			continue
		d, r, s = match.groups()
		dorm[d][r][s] = character
	for d in dorm:
		other_dorms = [dd for dd in dorm if dd != d]
		for r in dorm[d]:
			other_rooms = [rr for rr in dorm[d] if rr != r]
			for stu0 in dorm[d][r].values():
				for rr in other_rooms:
					for stu1 in dorm[d][rr].values():
						assert not list(
							engine.turns_when(
								stu0.unit.only.historical('location') ==
								stu1.unit.only.historical(
									'location') == 'dorm{}room{}'.format(d, r))
						), "{} seems to share a room with {}".format(
							stu0.name, stu1.name)
				common = 'common{}'.format(d)
				for dd in other_dorms:
					for rr in dorm[dd]:
						for stu1 in dorm[dd][rr].values():
							assert not list(
								engine.turns_when(
									stu0.unit.only.historical('location') ==
									stu1.unit.only.historical(
										'location') == common)
							), "{} seems to have been in the same common room  as {}".format(
								stu0.name, stu1.name)


def test_noncollision_premade(college24_premade):
	noncollision(college24_premade)


def test_windows_intersection():
	assert windows_intersection([(2, None), (0, 1)]) == []
	assert windows_intersection([(1, 2), (0, 1)]) == [(1, 1)]


def test_graph_val_select_eq(engy):
	assert engy.turn == 0
	me = engy.new_character('me')
	me.stat['foo'] = 'bar'
	me.stat['qux'] = 'bas'
	engy.next_turn()
	assert engy.turn == 1
	me.stat['foo'] = ''
	me.stat['foo'] = 'bas'
	me.stat['qux'] = 'bar'
	engy.next_turn()
	assert engy.turn == 2
	me.stat['qux'] = 'bas'
	engy.next_turn()
	assert engy.turn == 3
	me.stat['qux'] = 'bar'
	engy.next_turn()
	assert engy.turn == 4
	engy.branch = 'leaf'
	assert engy.turn == 4
	engy.next_turn()
	assert engy.turn == 5
	me.stat['foo'] = 'bar'
	engy.next_turn()
	assert engy.turn == 6
	me.stat['foo'] = 'bas'
	me.stat['qux'] = 'bas'
	engy.next_turn()
	assert engy.turn == 7
	foo_alias = me.historical('foo')
	qux_alias = me.historical('qux')
	qry = foo_alias == qux_alias
	turn_end_result = engy.turns_when(qry)
	assert 5 in turn_end_result
	assert 3 not in turn_end_result
	assert turn_end_result == set(turn_end_result) == {2, 5, 6, 7}
	mid_turn_result = engy.turns_when(qry, mid_turn=True)
	assert 3 in mid_turn_result
	assert 4 not in mid_turn_result
	assert mid_turn_result == set(mid_turn_result) == {1, 2, 3, 5, 6, 7}


def test_stress_graph_val_select_eq(engy):
	import random
	from time import monotonic
	me = engy.new_character('me')
	me.stat['qux'] = random.choice(['foo', 'bar', 'bas'])
	me.stat['quux'] = random.choice(['foo', 'bar', 'bas'])
	for i in range(10000):
		engy.next_turn()
		me.stat['qux'] = random.choice(['foo', 'bar', 'bas'])
		me.stat['quux'] = random.choice(['foo', 'bar', 'bas'])
	qry = me.historical('qux') == me.historical('quux')
	start_ts = monotonic()
	engy.turns_when(qry)
	assert monotonic() - start_ts < 1


def test_graph_val_select_lt_gt(engy):
	me = engy.new_character('me')
	me.stat['foo'] = 10
	me.stat['bar'] = 1
	engy.next_turn()
	me.stat['foo'] = 2
	me.stat['bar'] = 8
	engy.next_turn()
	me.stat['foo'] = 3
	engy.next_turn()
	me.stat['foo'] = 9
	engy.next_turn()
	engy.branch = 'leaf'
	me.stat['bar'] = 5
	engy.next_turn()
	me.stat['bar'] = 2
	engy.next_turn()
	me.stat['bar'] = 10
	engy.next_turn()
	me.stat['bar'] = 1
	engy.next_turn()
	me.stat['bar'] = 10
	foo_hist = me.historical('foo')
	bar_hist = me.historical('bar')
	res = engy.turns_when(foo_hist < bar_hist)
	assert set(res) == {1, 2, 6, 8}
	res = engy.turns_when(foo_hist > bar_hist)
	assert set(res) == {0, 3, 4, 5, 7}


def test_stress_graph_val_select_lt(engy):
	import random
	from time import monotonic
	me = engy.new_character('me')
	me.stat['foo'] = random.randrange(0, 10)
	me.stat['bar'] = random.randrange(0, 10)
	for i in range(10000):
		engy.next_turn()
		me.stat['foo'] = random.randrange(0, 10)
		me.stat['bar'] = random.randrange(0, 10)
	qry = me.historical('foo') < me.historical('bar')
	start_ts = monotonic()
	engy.turns_when(qry)
	assert monotonic() - start_ts < 1
