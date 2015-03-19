# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013-2014 Zachary Spector,  zacharyspector@gmail.com
"""Editors for textual data in the database.

The data is accessed via a "store" -- a mapping onto the table, used
like a dictionary. Each of the widgets defined here,
:class:`StringsEditor` and :class:`FuncsEditor`, displays a list of
buttons with which the user may select one of the keys in the store,
and edit its value in a text box.

Though they retrieve data the same way, these widgets have different
ways of saving data -- the contents of the :class:`FuncsEditor` input
will be compiled into Python bytecode, stored along with the source
code.

"""
from collections import defaultdict
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.adapters.models import SelectableDataItem
from kivy.properties import (
    AliasProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    OptionProperty,
    StringProperty
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import ListView, ListItemButton
from kivy.adapters.listadapter import ListAdapter
from .codeinput import FunctionInput
from .stringinput import StringInput


class StoreDataItem(EventDispatcher, SelectableDataItem):
    """Stores ``name`` and ``source``, and remembers whether an item with
    its name is selected or not. If so, that means this very item
    should be selected as well -- probably it got destroyed and
    recreated when we were saving and loading.

    """
    name = ObjectProperty()
    source = StringProperty()
    selectedness = defaultdict(lambda: False)  # class property
    is_selected = AliasProperty(
        lambda self: self.selectedness[str(self.name)],
        lambda self, v: self.selectedness.__setitem__(str(self.name), v)
    )


class StoreButton(ListItemButton):
    """Really just a :class:`ListItemButton` with properties for some
    metadata I might want.

    """
    store = ObjectProperty()
    table = StringProperty('function')
    name = ObjectProperty()
    source = StringProperty()


class StoreAdapter(ListAdapter):
    """:class:`ListAdapter` used to make lists of :class:`StoreButton`.

    """
    table = StringProperty('function')
    store = ObjectProperty()
    loader = ObjectProperty()

    def __init__(self, **kwargs):
        """Initialize with empty ``data``, the :class:`StoreButton` ``cls``,
        an appropriate ``args_converter``,
        ``selection_mode``=``single`` and
        ``allow_empty_selection``=``False``.

        """
        kwargs['data'] = []
        kwargs['cls'] = StoreButton
        kwargs['args_converter'] = lambda i, storedata: {
            'store': self.store,
            'table': self.table,
            'text': str(storedata.name),
            'name': storedata.name,
            'source': storedata.source,
            'on_press': lambda inst: self.loader(),
            'size_hint_y': None,
            'height': 30
        }
        kwargs['selection_mode'] = 'single'
        kwargs['allow_empty_selection'] = False
        kwargs['propagate_selection_to_data'] = True
        super().__init__(**kwargs)

    def get_data(self):
        """Override this to return the appropriate data from my store in a
        list.

        """
        raise NotImplementedError


class FuncStoreAdapter(StoreAdapter):
    """:class:`StoreAdapter` that wraps a function store. Gets function
    names paired with their source code in plaintext.

    """

    def get_data(self, *args):
        """Get data from
        ``LiSE.query.QueryEngine.func_table_name_plaincode``.

        """
        return [
            StoreDataItem(name=k, source=v) for (k, v) in
            self.store.iterplain()
        ]


class StringStoreAdapter(StoreAdapter):
    """:class:`StoreAdapter` that wraps a string store. Gets string names
    paired with their plaintext.

    """

    def get_data(self, *args):
        """Get data from ``LiSE.query.QueryEngine.string_table_lang_items``.

        """
        return [
            StoreDataItem(name=k, source=v) for (k, v) in
            self.store.lang_items()
        ]


class StoreList(FloatLayout):
    """Holder for a :class:`kivy.uix.listview.ListView` that shows what's
    in a store, using one of the StoreAdapter classes.

    """
    table = StringProperty()
    store = ObjectProperty()
    selection = ListProperty([])
    saver = ObjectProperty()

    def __init__(self, **kwargs):
        self._trigger_remake = Clock.create_trigger(self.remake)
        self._trigger_redata = Clock.create_trigger(self.redata)
        self.bind(
            table=self._trigger_remake,
            store=self._trigger_remake
        )
        super().__init__(**kwargs)

    def changed_selection(self, adapter):
        self.saver()
        self.selection = adapter.selection

    def remake(self, *args):
        """Make a new :class:`ListView`, add it to me, and then trigger
        ``redata`` to fill it with useful stuff.

        """
        if None in (self.store, self.table):
            return
        self.clear_widgets()
        self._adapter = self.adapter_cls(
            table=self.table,
            store=self.store,
            loader=self._trigger_redata
        )
        self._adapter.bind(
            on_selection_change=self.changed_selection
        )
        self.bind(
            table=self._adapter.setter('table'),
            store=self._adapter.setter('store')
        )
        self._listview = ListView(
            adapter=self._adapter
        )
        self.add_widget(self._listview)
        self._trigger_redata()

    def redata(self, *args):
        self._adapter.data = self._adapter.get_data()


class FuncStoreList(StoreList):
    adapter_cls = FuncStoreAdapter


class StringStoreList(StoreList):
    adapter_cls = StringStoreAdapter


class StoreEditor(BoxLayout):
    """StoreList on the left with its editor on the right."""
    table = StringProperty()
    store = ObjectProperty()
    font_name = StringProperty('DroidSans')
    font_size = NumericProperty(12)
    selection = ListProperty([])
    oldsel = ListProperty([])
    name = StringProperty()
    source = StringProperty()

    def __init__(self, **kwargs):
        self._trigger_save = Clock.create_trigger(self.save)
        self._trigger_remake = Clock.create_trigger(self.remake)
        self._trigger_redata_reselect = Clock.create_trigger(
            self.redata_reselect
        )
        self.bind(
            table=self._trigger_remake,
            store=self._trigger_remake
        )
        super().__init__(**kwargs)

    def remake(self, *args):
        if None in (self.store, self.table):
            return
        self.clear_widgets()
        self._list = self.list_cls(
            size_hint_x=0.4,
            table=self.table,
            store=self.store,
            saver=self.save
        )
        self._list.bind(selection=self.changed_selection)
        self.bind(
            table=self._list.setter('table'),
            store=self._list.setter('store')
        )
        self.add_widget(self._list)
        self.add_editor()

    def changed_selection(self, *args):
        if self._list.selection:
            self.selection = self._list.selection
            self.name = self.selection[0].name
            self.source = self.selection[0].source

    def redata_reselect(self, *args):
        self.save()
        StoreDataItem.selectedness = defaultdict(lambda: False)
        StoreDataItem.selectedness[self.name] = True
        self._list._trigger_redata()

    def add_editor(self, *args):
        """Construct whatever editor widget I use and add it to myself."""
        raise NotImplementedError

    def save(self, *args):
        """Write my editor's changes to disk."""
        raise NotImplementedError


class StringsEditor(StoreEditor):
    list_cls = StringStoreList

    def add_editor(self, *args):
        if self.selection is None:
            Clock.schedule_once(self.add_editor, 0)
            return
        self._editor = StringInput(
            font_name=self.font_name,
            font_size=self.font_size
        )
        self.bind(
            font_name=self._editor.setter('font_name'),
            font_size=self._editor.setter('font_size'),
            name=self._editor.setter('name'),
            source=self._editor.setter('source')
        )
        self.add_widget(self._editor)

    def save(self, *args):
        self.source = self._editor.source
        if self.name != self._editor.name:
            del self.store[self.name]
            self.name = self._editor.name
        self.store[self.name] = self.source


class FuncsEditor(StoreEditor):
    params = ListProperty(['engine', 'character'])
    subject_type = OptionProperty(
        'character', options=['character', 'thing', 'place', 'portal']
    )
    list_cls = FuncStoreList

    def on_params(self, *args):
        if self.params == ['engine', 'character']:
            self.subject_type = 'character'
        elif self.params == ['engine', 'character', 'thing']:
            self.subject_type = 'thing'
        elif self.params == ['engine', 'character', 'place']:
            self.subject_type = 'place'
        elif self.params == ['engine', 'character', 'origin', 'destination']:
            self.subject_type = 'portal'
        else:
            raise ValueError(
                "Unsupported function signature: {}".format(self.params)
            )

    def add_editor(self, *args):
        if None in (self.selection, self.params):
            Clock.schedule_once(self.add_editor, 0)
            return
        self._editor = FunctionInput(
            font_name=self.font_name,
            font_size=self.font_size,
            params=self.params,
        )
        self.bind(
            font_name=self._editor.setter('font_name'),
            font_size=self._editor.setter('font_size'),
            name=self._editor.setter('name'),
            source=self._editor.setter('source')
        )
        self._editor.bind(params=self.setter('params'))
        self.add_widget(self._editor)

    def save(self, *args):
        if '' in (self._editor.name, self._editor.source):
            return
        if (
                self.name == self._editor.name and
                self.source == self._editor.source
        ):
            return
        if self.name != self._editor.name:
            del self.store[self.name]
        self.name = self._editor.name
        self.source = self._editor.source
        Logger.debug(
            'saving function {}={}'.format(
                self.name,
                self.source
            )
        )
        self.store.db.func_table_set_source(
            self.table,
            self.name,
            self.source
        )
