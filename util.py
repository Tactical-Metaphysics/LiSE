class LocationException(Exception):
    pass


class ContainmentException(Exception):
    pass


class SenselessEventException(Exception):
    pass


class ImpossibleEventException(Exception):
    pass


class IrrelevantEventException(Exception):
    pass


class ImpracticalEventException(Exception):
    pass


class SaveableMetaclass(type):
    def __new__(metaclass, clas, parents, attrs):
        if 'coldecls' not in attrs:
            raise Exception("No coldecls in {0}".format(clas))
        if 'primarykeys' not in attrs:
            raise Exception("no primarykeys in {0}".format(clas))
        coldecls = attrs['coldecls']
        primarykeys = attrs['primarykeys']
        tablenames = attrs['tablenames']

        if 'foreignkeys' in attrs:
            foreignkeys = attrs['foreignkeys']
        else:
            foreignkeys = {}

        if 'checks' in attrs:
            checks = attrs['checks']
        else:
            checks = {}
        for d in foreignkeys, checks:
            for tablename in tablenames:
                if tablename not in d:
                    d[tablename] = {}
        schemata = []
        inserts = {}
        deletes = {}
        detects = {}
        missings = {}
        keylen = {}
        rowlen = {}
        keyqms = {}
        rowqms = {}
        keystrs = {}
        rowstrs = {}
        keynames = {}
        valnames = {}
        colnames = {}
        colnamestr = {}
        for item in primarykeys.iteritems():
            (tablename, pkey) = item
            keynames[tablename] = sorted(pkey)
            keylen[tablename] = len(pkey)
            keyqms[tablename] = ", ".join(["?"] * keylen[tablename])
            keystrs[tablename] = "(" + keyqms[tablename] + ")"
        for item in coldecls.iteritems():
            (tablename, coldict) = item
            valnames[tablename] = sorted(
                [key for key in coldict.keys()
                 if key not in keynames[tablename]])
            rowlen[tablename] = len(coldict)
            rowqms[tablename] = ", ".join(["?"] * rowlen[tablename])
            rowstrs[tablename] = "(" + rowqms[tablename] + ")"
        for tablename in coldecls.iterkeys():
            colnames[tablename] = keynames[tablename] + valnames[tablename]
        for tablename in tablenames:
            coldecl = coldecls[tablename]
            pkey = primarykeys[tablename]
            fkeys = foreignkeys[tablename]
            cks = ["CHECK(%s)" % ck for ck in checks[tablename]]
            pkeydecs = [keyname + " " + typ.upper()
                        for (keyname, typ) in coldecl.iteritems()
                        if keyname in pkey]
            valdecs = [valname + " " + typ.upper()
                       for (valname, typ) in coldecl.iteritems()
                       if valname not in pkey]
            coldecs = sorted(pkeydecs) + sorted(valdecs)
            coldecstr = ", ".join(coldecs)
            pkeycolstr = ", ".join(pkey)
            pkeys = [keyname for (keyname, typ) in coldecl.iteritems()
                     if keyname in pkey]
            pkeynamestr = ", ".join(sorted(pkeys))
            vals = [valname for (valname, typ) in coldecl.iteritems()
                    if valname not in pkey]
            colnamestr[tablename] = ", ".join(sorted(pkeys) + sorted(vals))
            pkeystr = "PRIMARY KEY (%s)" % (pkeycolstr,)
            fkeystrs = ["FOREIGN KEY (%s) REFERENCES %s(%s)" %
                        (item[0], item[1][0], item[1][1])
                        for item in fkeys.iteritems()]
            fkeystr = ", ".join(fkeystrs)
            chkstr = ", ".join(cks)
            table_decl_data = [coldecstr]
            if len(pkey) > 0:
                table_decl_data.append(pkeystr)
            if len(fkeystrs) > 0:
                table_decl_data.append(fkeystr)
            if len(cks) > 0:
                table_decl_data.append(chkstr)
            table_decl = ", ".join(table_decl_data)
            create_stmt = "CREATE TABLE %s (%s);" % (tablename, table_decl)
            insert_stmt_start = "INSERT INTO %s VALUES " % (
                tablename,)
            inserts[tablename] = insert_stmt_start
            delete_stmt_start = "DELETE FROM %s WHERE (%s) IN " % (
                tablename, pkeycolstr)
            deletes[tablename] = delete_stmt_start
            detect_stmt_start = "SELECT %s FROM %s WHERE (%s) IN " % (
                colnamestr[tablename], tablename, pkeynamestr)
            detects[tablename] = detect_stmt_start
            missing_stmt_start = "SELECT %s FROM %s WHERE (%s) NOT IN " % (
                colnamestr[tablename], tablename, pkeynamestr)
            missings[tablename] = missing_stmt_start
            schemata.append(create_stmt)

        def insert_rowdicts_table(db, rowdicts, tabname):
            rowstr = rowstrs[tabname]
            qrystr = inserts[tabname] + ", ".join([rowstr] * len(rowdicts))
            qrylst = []
            for rowdict in rowdicts:
                extender = [rowdict[col] for col in colnames[tabname]]
                qrylst.extend(extender)
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def delete_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = deletes[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def detect_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = detects[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def missing_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = missings[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def insert_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabn, rd) = item
                if isinstance(rd, list):
                    insert_rowdicts_table(db, rd, tabn)
                else:
                    insert_rowdicts_table(db, [rd], tabn)

        def delete_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabn, rd) = item
                delete_keydicts_table(db, rd, tabn)

        def detect_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabn, rd) = item
                return detect_keydicts_table(db, rd, tabn)

        def missing_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabn, rd) = item
                return missing_keydicts_table(db, rd, tabn)

        def unravel(self, db):
            pass

        dbop = {'insert': insert_tabdict,
                'delete': delete_tabdict,
                'detect': detect_tabdict,
                'missing': missing_tabdict}
        atrdic = {'coldecls': coldecls,
                  'colnames': colnames,
                  'colnamestr': colnamestr,
                  'keynames': keynames,
                  'valnames': valnames,
                  'cols': colnames[tablenames[0]],
                  'primarykeys': primarykeys,
                  'foreignkeys': foreignkeys,
                  'checks': checks,
                  'schemata': schemata,
                  'keylen': keylen,
                  'rowlen': rowlen,
                  'keyqms': keyqms,
                  'rowqms': rowqms,
                  'dbop': dbop,
                  'unravel': unravel,
                  'maintab': tablenames[0]}
        atrdic.update(attrs)

        return type.__new__(metaclass, clas, parents, atrdic)


def start_new_map(nope):
    pass


def open_map(nope):
    pass


def save_map(nope):
    pass


def quit_map_editor(nope):
    pass


def editor_select(nope):
    pass


def editor_copy(nope):
    pass


def editor_paste(nope):
    pass


def editor_delete(nope):
    pass


def new_place(place_type):
    pass


def new_thing(thing_type):
    pass


funcs = [start_new_map, open_map, save_map, quit_map_editor, editor_select,
         editor_copy, editor_paste, editor_delete, new_place, new_thing]


def mkitemd(dimension, name):
    return {'dimension': dimension,
            'name': name}


def reciprocate(porttup):
    return (porttup[1], porttup[0])


def reciprocate_all(porttups):
    return [reciprocate(port) for port in porttups]


def reciprocal_pairs(pairs):
    return pairs + [reciprocate(pair) for pair in pairs]


def mkportald(dimension, orig, dest):
    return {'dimension': dimension,
            'name': "portal[%s->%s]" % (orig, dest),
            'from_place': orig,
            'to_place': dest}


def mklocd(dimension, thing, place):
    return {'dimension': dimension,
            'thing': thing,
            'place': place}


def mkstepd(dimension, thing, idx, portal):
    return {"dimension": dimension,
            "thing": thing,
            "idx": idx,
            "portal": portal}


def translate_color(name, rgb):
    return {
        'name': name,
        'red': rgb[0],
        'green': rgb[1],
        'blue': rgb[2],
        'alpha': 255}


def mkcontd(dimension, contained, container):
    # I have not made any containments yet
    return {"dimension": dimension,
            "contained": contained,
            "container": container}


def mkjourneyd(thing):
    return {"dimension": "Physical",
            "thing": thing,
            "curstep": 0,
            "progress": 0.0}


def mkboardd(dimension, width, height, wallpaper):
    return {"dimension": dimension,
            "width": width,
            "height": height,
            "wallpaper": wallpaper}


def mkboardmenud(board, menu):
    return {"board": board,
            "menu": menu}


def mkimgd(name, path, rltile):
    return {"name": name,
            "path": path,
            "rltile": rltile}


def mkspotd(dimension, place, img, x, y, visible, interactive):
    return {"dimension": dimension,
            "place": place,
            "img": img,
            "x": x,
            "y": y,
            "visible": visible,
            "interactive": interactive}


def mkpawnd(dimension, thing, img, visible, interactive):
    return {"dimension": dimension,
            "thing": thing,
            "img": img,
            "visible": visible,
            "interactive": interactive}


def mkstyled(name, fontface, fontsize, spacing,
             bg_inactive, bg_active,
             fg_inactive, fg_active):
    return {'name': name,
            'fontface': fontface,
            'fontsize': fontsize,
            'spacing': spacing,
            'bg_inactive': bg_inactive,
            'bg_active': bg_active,
            'fg_inactive': fg_inactive,
            'fg_active': fg_active}


def untuple(list_o_tups):
    r = []
    for tup in list_o_tups:
        for val in tup:
            r.append(val)
    return r


def dictify_row(row, colnames):
    return dict(zip(colnames, row))


def dictify_rows(rows, keynames, colnames):
    # Produce a dictionary with which to look up rows--but rows that
    # have themselves been turned into dictionaries.
    r = {}
    # Start this dictionary with empty dicts, deep enough to hold
    # all the partial keys in keynames and then a value.
    # I think this fills deeper than necessary?
    keys = len(keynames)  # use this many fields as keys
    for row in rows:
        ptr = r
        i = 0
        while i < keys:
            i += 1
            try:
                ptr = ptr[row[i]]
            except:
                ptr = {}
        # Now ptr points to the dict of the last key that doesn't get
        # a dictified row. i is one beyond that.
        ptr[row[i]] = dictify_row(row)
    return r


def dicl2tupl(dicl):
    # Converts list of dicts with one set of keys to list of tuples of
    # *values only*, not keys. They'll be in the same order as given
    # by dict.keys().
    keys = dicl[0].keys()
    r = []
    for dic in dicl:
        l = [dic[k] for k in keys]
        r.append(tuple(l))
    return r


def deep_lookup(dic, keylst):
    key = keylst.pop()
    ptr = dic
    while keylst != []:
        ptr = ptr[key]
        key = keylst.pop()
    return ptr[key]


def compile_tabdicts(objs):
    tabdicts = [o.tabdict for o in objs]
    mastertab = {}
    for tabdict in tabdicts:
        for item in tabdict.iteritems():
            (tabname, rowdict) = item
            if tabname not in mastertab:
                mastertab[tabname] = []
            mastertab[tabname].append(rowdict)
    return mastertab

def deep_lookup(dic, keylst):
    key = keylst.pop()
    ptr = dic
    while keylst != []:
        ptr = ptr[key]
        key = keylst.pop()
    return ptr[key]
