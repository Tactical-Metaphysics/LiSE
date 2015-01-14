# This file is part of LiSE, a framework for life simulation games.
# Copyright (C) 2013-2014 Zachary Spector, ZacharySpector@gmail.com
"""Grid of current values for some entity. Can be changed by the
user. Autoupdates when there's a change for any reason.

"""
from functools import partial
from kivy.properties import (
    BooleanProperty,
    DictProperty,
    ObjectProperty
)
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.slider import Slider
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.textinput import TextInput
from kivy.uix.listview import (
    SelectableView,
    ListView,
    ListItemLabel,
    ListItemButton,
    CompositeListItem
)
from kivy.adapters.dictadapter import DictAdapter
from kivy.lang import Builder
from ELiDE.remote import MirrorMapping


class StatRowTextInput(TextInput, SelectableView):
    def __init__(self, **kwargs):
        kwargs['multiline'] = False
        self._trigger_upd_value = Clock.create_trigger(self.upd_value)
        super().__init__(**kwargs)

        def lost_focus(self, *args):
            if not self.focus:
                self._trigger_upd_value()

        self.bind(
            on_enter=self._trigger_upd_value,
            on_text_validate=self._trigger_upd_value,
            on_focus=lost_focus
        )

    def upd_value(self, *args):
        if self.text == '':
            self.parent.value = None
        else:
            self.parent.value = self.text
        self.parent.set_value()
        self.text = ''


class StatRowToggleButton(ToggleButtonBehavior, ListItemButton):
    def __init__(self, **kwargs):
        self._trigger_upd_value = Clock.create_trigger(self.upd_value)
        self.bind(on_touch_up=self._trigger_upd_value)
        super().__init__(**kwargs)

    def upd_value(self, *args):
        if self.parent is None:
            return
        if (
            self.state == 'normal' and self.parent.value == 0
        ) or (
            self.state == 'down' and self.parent.value == 1
        ):
            return
        if self.state == 'normal':
            self.parent.value = 0
        else:
            self.parent.value = 1
        self.parent.set_value()


class StatRowSlider(Slider, SelectableView):
    need_set = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._trigger_maybe_set = Clock.create_trigger(self.maybe_set)
        super().__init__(**kwargs)
        self.bind(on_touch_up=self._trigger_maybe_set)

    def on_value(self, *args):
        self.need_set = True

    def maybe_set(self, *args):
        if self.need_set:
            self.parent.value = self.value
            self.parent.set_value()
            self.need_set = False


class StatRowListItem(CompositeListItem):
    key = ObjectProperty()
    value = ObjectProperty(None, allownone=True)
    reg = ObjectProperty()
    unreg = ObjectProperty()
    setter = ObjectProperty()

    def set_value(self, *args):
        self.setter(self.key, self.value)

    def on_parent(self, *args):
        if self.parent is None:
            self.unreg(self)
        else:
            self.reg(self)


control_cls = {
    'readout': lambda v: {
        'cls': ListItemLabel,
        'kwargs': {
            'text': str(v)
        }
    },
    'textinput': lambda v: {
        'cls': StatRowTextInput,
        'kwargs': {
            'text': str(v)
        }
    },
    'togglebutton': lambda v: {
        'cls': StatRowToggleButton,
        'kwargs': {
            'state': 'down' if v else 'normal'
        }
    },
    'slider': lambda v: {
        'cls': StatRowSlider,
        'kwargs': {'value': v, 'text': str(v)}
    }
}


control_txt = {
    'readout': 'Readout',
    'textinput': 'Text input',
    'togglebutton': 'Toggle button',
    'slider': 'Slider'
}


class StatListView(ListView, MirrorMapping):
    layout = ObjectProperty()

    def __init__(self, **kwargs):
        kwargs['adapter'] = self.get_adapter()
        self._trigger_sortkeys = Clock.create_trigger(self.sortkeys)
        self._trigger_upd_data = Clock.create_trigger(self.upd_data)
        self.bind(mirror=self._trigger_sortkeys)
        self.bind(
            mirror=self._trigger_upd_data,
            time=self._trigger_upd_data
        )
        self._listeners = {}
        super().__init__(**kwargs)

    def on_layout(self, *args):
        self.remote = self.layout.selected_remote
        self.layout.bind(
            selected_remote=self.setter('remote')
        )
        self.layout.bind(
            character=self._reremote,
            selection=self._reremote
        )

    def set_value(self, k, v):
        self.layout.set_remote_value(self.remote, k, v)

    def get_adapter(self):
        return DictAdapter(
            data=self.get_data(),
            cls=StatRowListItem,
            args_converter=lambda i, kv: {
                'key': kv[0],
                'value': kv[1],
                'reg': self.reg_widget,
                'unreg': self.unreg_widget,
                'setter': self.set_value,
                'cls_dicts': self.get_cls_dicts(*kv)
            },
            selection_mode='multiple',
            allow_empty_selection=True
        )

    def get_cls_dicts(self, key, value):
        keydict = {
            'cls': ListItemLabel,
            'kwargs': {'text': str(key)}
        }
        control_type = self.mirror['_control'].get(key, 'textinput')
        valdict = control_cls[control_type](value)
        override = dict(self.mirror['_config'].get(key, {}))
        # hack to let you choose how to display boolean values
        for (k, v) in override.items():
            Logger.debug('StatListView: overriding {}={}'.format(k, v))
        true_text = '1'
        if 'true_text' in override:
            true_text = override['true_text']
            del override['true_text']
        false_text = '0'
        if 'false_text' in override:
            false_text = override['false_text']
            del override['false_text']
        valdict['kwargs'].update(override)
        valdict['kwargs']['text'] = true_text if value else false_text
        return [keydict, valdict]

    def get_data(self):
        return {
            k: (k, v) for (k, v) in self.mirror.items()
            if (
                k[0] != '_' and
                k not in (
                    'character',
                    'name',
                    'location',
                    'next_location',
                    'locations',
                    'arrival_time',
                    'next_arrival_time'
                ) or not isinstance(k, str)
            )
        }

    def upd_data(self, *args):
        self.adapter.data = self.get_data()

    def sortkeys(self, *args):
        for key in self.mirror.keys():
            if key not in self.adapter.sorted_keys:
                self.adapter.sorted_keys = sorted(self.mirror.keys())
                return
        seen = set()
        for k in self.adapter.sorted_keys:
            if k not in seen and k not in self.mirror:
                self.adapter.sorted_keys.remove(k)
            seen.add(k)

    def reg_widget(self, w, *args):
        if not self.mirror:
            Clock.schedule_once(partial(self.reg_widget, w), 0)
            return

        def listen(*args):
            if w.key not in self.mirror:
                return
            if w.value != self.mirror[w.key]:
                w.value = self.mirror[w.key]
        self._listeners[w.key] = listen
        self.bind(mirror=listen)

    def unreg_widget(self, w):
        if w.key in self._listeners:
            self.unbind(mirror=self._listeners[w.key])


class SelectableTextInput(TextInput, SelectableView):
    def select_from_composite(self, *args):
        pass

    def deselect_from_composite(self, *args):
        pass


class IntInput(SelectableTextInput):
    def insert_text(self, s, from_undo=False):
        return super().insert_text(
            ''.join(c for c in s if c in '0123456789'),
            from_undo
        )


class ControlTypePicker(ListItemButton):
    key = ObjectProperty()
    mainbutton = ObjectProperty()
    dropdown = ObjectProperty()
    setter = ObjectProperty()
    button_kwargs = DictProperty()
    dropdown_kwargs = DictProperty()
    control_texts = DictProperty()
    control_callbacks = DictProperty()

    def __init__(self, **kwargs):
        if 'button_kwargs' not in kwargs:
            kwargs['button_kwargs'] = {}
        if 'dropdown_kwargs' not in kwargs:
            kwargs['dropdown_kwargs'] = {}
        super().__init__(**kwargs)
        self.build()

    def selected(self, v):
        self.setter(self.key, v)
        self.text = str(v)

    def build(self, *args):
        if None in (
                self.key,
                self.setter,
                self.button_kwargs,
                self.dropdown_kwargs,
                self.control_texts,
                self.control_callbacks
        ):
            Clock.schedule_once(self.build, 0)
            return
        self.mainbutton = None
        self.dropdown = None
        self.dropdown = DropDown(
            text=self.text,
            on_select=lambda instance, x: self.selected(x),
            **self.dropdown_kwargs
        )
        self.dropdown.add_widget(
            Button(
                text='Readout',
                size_hint_y=None,
                height=self.height,
                on_press=lambda instance: self.dropdown.select('readout')
            )
        )
        self.dropdown.add_widget(
            Button(
                text='Text input',
                size_hint_y=None,
                height=self.height,
                on_press=lambda instance: self.dropdown.select('textinput')
            )
        )
        self.dropdown.add_widget(
            Button(
                text='Toggle button',
                size_hint_y=None,
                height=self.height,
                on_press=lambda instance: self.dropdown.select('togglebutton')
            )
        )
        self.dropdown.add_widget(
            Button(
                text='Slider',
                size_hint_y=None,
                height=self.height,
                on_press=lambda instance: self.dropdown.select('slider')
            )
        )

        self.bind(on_press=self.dropdown.open)


class StatListViewConfigurator(StatListView):
    def del_key(self, key):
        if key in self.remote:
            del self.remote[key]
        if '_control' in self.mirror and key in self.mirror['_control']:
            ctrld = dict(self.mirror['_control'])
            del ctrld[key]
            self.remote['_control'] = ctrld
        if '_config' in self.mirror and key in self.mirror['_config']:
            cfgd = dict(self.mirror['_config'])
            del cfgd[key]
            self.remote['_config'] = cfgd
        if key in self.mirror:
            del self.mirror[key]
        if key in self.adapter.sorted_keys:
            self.adapter.sorted_keys.remove(key)

    def set_control_type(self, key, value, *args):
        if not isinstance(value, str):
            raise ValueError(
                "Tried to set {} to unknown control type {}".format(
                    key, value
                )
            )
        Logger.debug(
            'StatListViewConfigurator: set_control_type({}, {})'.format(
                key, value
            )
        )
        self.canvas.after.clear()
        ctrld = dict(self.mirror['_control'])
        ctrld[key] = value
        self.remote['_control'] = ctrld

    def get_adapter(self):
        return DictAdapter(
            data=self.get_data(),
            cls=CompositeListItem,
            args_converter=lambda i, kv: {
                'cls_dicts': self.get_cls_dicts(*kv)
            },
            selection_mode='multiple',
            allow_empty_selection=True
        )

    def set_control(self, key, control):
        if '_control' not in self.mirror:
            self.remote['_control'] = {key: control}
        elif key not in self.mirror['_control']:
            ctrld = dict(self.mirror['_control'])
            ctrld[key] = control
            self.remote['_control'] = ctrld

    def have_control(self, key):
        return (
            '_control' in self.mirror and
            key in self.mirror['_control']
        )

    def set_config(self, key, option, value):
        if '_config' not in self.mirror:
            self.remote['_config'] = {key: {option: value}}
        elif key not in self.mirror['_config']:
            cfgd = dict(self.mirror['_config'])
            cfgd[key] = {option: value}
            self.remote['_config'] = cfgd

    def have_config(self, key, option):
        return (
            '_config' in self.mirror and
            key in self.mirror['_config'] and
            option in self.mirror['_config'][key]
        )

    def get_cls_dicts(self, key, value):
        if not self.have_control(key):
            self.set_control(key, 'textinput')
        control_type = self.mirror['_control'][key]
        defaultcfg = {
            'true_text': '1',
            'false_text': '0',
            'min': 0.0,
            'max': 1.0
        }
        if '_config' not in self.mirror:
            self.remote['_config'] = {key: defaultcfg}
        elif key not in self.mirror['_config']:
            ctrld = dict(self.mirror['_config'])
            ctrld[key] = defaultcfg
            self.remote['_config'] = ctrld
        cfg = self.mirror['_config'][key]

        deldict = {
            'cls': ListItemButton,
            'kwargs': {
                'text': 'del',
                'on_press': partial(self.del_key, key)
            }
        }
        picker_dict = {
            'cls': ControlTypePicker,
            'kwargs': {
                'key': key,
                'text': control_type,
                'setter': self.set_control_type,
                'control_texts': control_txt,
                'dropdown_kwargs': {
                    'canvas': self.canvas.after
                }
            }
        }
        keydict = {
            'cls': ListItemLabel,
            'kwargs': {'text': str(key)}
        }
        valdict = {
            'cls': SelectableTextInput,
            'kwargs': {
                'text': str(value),
                'on_text_validate': lambda i, v: self.set_value(key, i.text),
                'on_enter': lambda i, v: self.set_value(key, i.text),
                'on_focus': lambda i, v:
                self.set_value(key, i.text) if not v else None
            }
        }
        cls_dicts = [
            deldict, keydict, valdict, picker_dict
        ]

        if control_type == 'togglebutton':
            true_text_dict = {
                'cls': SelectableTextInput,
                'kwargs': {
                    'multiline': False,
                    'hint_text': 'Text when true',
                    'text': str(cfg['true_text']),
                    'on_enter': lambda i, v:
                    self.set_config(key, 'true_text', i.text),
                    'on_text_validate': lambda i, v:
                    self.set_config(key, 'true_text', i.text),
                    'on_focus': lambda i, foc:
                    self.set_config(key, 'true_text', i.text)
                    if not foc else None
                }
            }
            false_text_dict = {
                'cls': SelectableTextInput,
                'kwargs': {
                    'multiline': False,
                    'hint_text': 'Text when false',
                    'text': str(cfg['false_text']),
                    'on_enter': lambda i, v:
                    self.set_config(key, 'false_text', i.text),
                    'on_text_validate': lambda i, v:
                    self.set_config(key, 'false_text', i.text),
                    'on_focus': lambda i, foc:
                    self.set_config(key, 'false_text', i.text)
                    if not foc else None
                }
            }
            cls_dicts.extend((true_text_dict, false_text_dict))

        if control_type == 'slider':
            min_dict = {
                'cls': IntInput,
                'kwargs': {
                    'multiline': False,
                    'hint_text': 'Minimum',
                    'text': str(cfg['min']),
                    'on_enter': lambda i, v:
                    self.set_config(key, 'min', float(i.text)),
                    'on_text_validate': lambda i, v:
                    self.set_config(key, 'min', float(i.text)),
                    'on_focus': lambda i, foc:
                    self.set_config(key, 'min', float(i.text))
                    if not foc else None
                }
            }
            max_dict = {
                'cls': IntInput,
                'kwargs': {
                    'multiline': False,
                    'hint_text': 'Maximum',
                    'text': str(cfg['max']),
                    'on_enter': lambda i, v:
                    self.set_config(key, 'max', float(i.text)),
                    'on_text_validate': lambda i, v:
                    self.set_config(key, 'max', float(i.text)),
                    'on_focus': lambda i, foc:
                    self.set_config(key, 'max', float(i.text))
                    if not foc else None
                }
            }
            cls_dicts.extend((min_dict, max_dict))
        return cls_dicts


kv = """
<StatRowListItem>:
    orientation: 'horizontal'
    height: 30
"""
Builder.load_string(kv)
