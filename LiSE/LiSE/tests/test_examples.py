from LiSE import Engine
from LiSE.examples import college, kobold, polygons, sickle


def test_college(engy):
    college.install(engy)
    engy.turn = 10  # wake up the students
    engy.next_turn()


def test_kobold(engy):
    kobold.inittest(engy, shrubberies=20, kobold_sprint_chance=.9)
    for i in range(10):
        engy.next_turn()


def test_polygons(engy):
    polygons.install(engy)
    for i in range(10):
        engy.next_turn()


def test_polygons_startup(tempdir):
    with Engine(tempdir) as eng:
        polygons.install(eng)
    with Engine(tempdir) as eng:
        for i in range(10):
            eng.next_turn()


def test_sickle(engy):
    sickle.install(engy)
    for i in range(100):
        engy.next_turn()
