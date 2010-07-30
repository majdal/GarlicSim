# Copyright 2009-2010 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

'''
This module defines the SimpackGrokker class and the InvalidSimpack exception.

See their documentation for more details.
'''

import functools
import types
import imp

from garlicsim.general_misc import import_tools
from garlicsim.general_misc import misc_tools
import garlicsim.general_misc.caching

from garlicsim.misc import (AutoClockGenerator, InvalidSimpack,
                            GarlicSimException, simpack_tools)
from garlicsim.misc import step_iterators as step_iterators_module
import misc

from .settings import Settings
from .get_step_type import get_step_type
from . import step_types


class SimpackGrokker(object):
    '''Encapsulates a simpack and gives useful information and tools.'''
    
    __metaclass__ = garlicsim.general_misc.caching.CachedType

    @staticmethod
    def create_from_state(state):
        simpack = simpack_tools.get_from_state(state)
        return SimpackGrokker(simpack)
    
    
    def __init__(self, simpack):
        self.simpack = simpack
        self.__init_analysis()
        self.__init_analysis_settings()

        
    def __init_analysis(self):
        '''Analyze the simpack.'''
        
        simpack = self.simpack
        
        try:
            State = simpack.State
        except AttributeError:
            raise InvalidSimpack('''The %s simpack does not define a `State` \
class.''' % simpack.__name__)
        
        if not issubclass(State, garlicsim.data_structures.State):
            raise InvalidSimpack('''The %s simpack defines a State class, but \
it's not a subclass of `garlicsim.data_structures.State`.''' % \
                                                             simpack.__name__)


        state_methods = dict(
            (name , value) for (name, value) in
            misc_tools.getted_vars(State).iteritems() if callable(value)
        )

        self.step_functions = dict((step_type, []) for step_type in
                                   step_types.step_types_list)
        

        for method in state_methods.itervalues():
            
            if 'step' in method.__name__:
                step_type = get_step_type(method)
                self.step_functions[step_type].append(method)
            
        
        all_step_functions = reduce(list.__add__,
                                    self.step_functions.itervalues())
        if not all_step_functions:
            raise InvalidSimpack("The %s simpack has not defined any kind "
                                 "of step function." % simpack.__name__)
        
                
        if self.step_functions[step_types.HistoryStep] or \
           self.step_functions[step_types.HistoryStepGenerator]:
            
            self.history_dependent = True
            
            self.default_step_function = (
                self.step_functions[step_types.HistoryStepGenerator] + \
                self.step_functions[step_types.HistoryStep]
            )[0]
            
            if self.step_functions[step_types.SimpleStep] or \
               self.step_functions[step_types.StepGenerator] or \
               self.step_functions[step_types.InplaceStep] or \
               self.step_functions[step_types.InplaceStepGenerator]:
                
                raise InvalidSimpack("The %s simpack is defining both a "
                                     "history-dependent step and a "
                                     "non-history-dependent step - which "
                                     "is forbidden." % simpack.__name__)
        else: # No history step defined
            
            self.history_dependent = False
            
            self.default_step_function = (
                self.step_functions[step_types.StepGenerator] + \
                self.step_functions[step_types.SimpleStep] + \
                self.step_functions[step_types.InplaceStepGenerator] + \
                self.step_functions[step_types.InplaceStep]
            )[0]
            
        
        
    
    def __init_analysis_settings(self):
        '''Analyze the simpack to produce a Settings object.'''
        # todo: consider doing this in Settings.__init__
        
        # We want to access the `.settings` of our simpack, but we don't know if
        # our simpack is a module or some other kind of object. So if it's a
        # module, we'll `try` to import `settings`.
        
        self.settings = Settings()        
        
        if isinstance(self.simpack, types.ModuleType) and \
           not hasattr(self.simpack, 'settings'):
            
            # The `if` that we did here means: "If there's reason to suspect
            # that self.simpack.settings is a module that exists but hasn't been
            # imported yet."
            
            settings_module_name = ''.join((
                self.simpack.__name__,
                '.settings'
            ))
            
            import_tools.import_if_exists(settings_module_name)
            # This imports the `settings` submodule, if it exists, but it
            # does *not* keep a reference to it. We'll access `settings` as
            # an attribute of the simpack below.
            
        # Checking if there are original settings at all. If there aren't, we're
        # done.
        if hasattr(self.simpack, 'settings'):
            
            original_settings = getattr(self.simpack, 'settings')
            
            for (key, value) in vars(self.settings).iteritems():
                if hasattr(original_settings, key):
                    actual_value = getattr(original_settings, key)
                    setattr(self.settings, key, actual_value)
            # todo: currently throws away unrecognized attributes from the
            # simpack's settings.
                
    
    """ tododoc: is this really needed? Can be done as a call to step_generator
    def step(self, state_or_history_browser, step_profile):
        '''
        Perform a step of the simulation.
        
        The step profile will specify which parameters to pass to the simpack's
        step function.
        '''
        
        auto_clock_generator = AutoClockGenerator()
        if isinstance(state_or_history_browser,
                      garlicsim.data_structures.State):
            state = state_or_history_browser
        else:
            state = state_or_history_browser.get_last_state()
        auto_clock_generator.make_clock(state)

        if self.simple_step_defined:
            step_function = self.simpack.history_step if \
                          self.history_dependent else self.simpack.State.step
            result = step_function(state_or_history_browser,
                                   *step_profile.args,
                                   **step_profile.kwargs)
        else: # self.step_generator_defined is True
            step_generator = self.simpack.history_step_generator if \
                          self.history_dependent else \
                          self.simpack.State.step_generator
            iterator = step_generator(state_or_history_browser,
                                      *step_profile.args,
                                      **step_profile.kwargs)
            result = iterator.next()
            
        result.clock = auto_clock_generator.make_clock(result)
        return result
    """
        
    
    def get_step_iterator(self, state_or_history_browser, step_profile):
        '''
        Step generator for crunching states of the simulation.
        
        The step profile will specify which parameters to pass to the simpack's
        step function.
        '''
        
        step_function = step_profile.step_function
        step_type = get_step_type(step_function)
        step_iterator_class = step_type.step_iterator_class

        step_iterator = step_iterator_class(state_or_history_browser,
                                            step_profile)
        
        return step_iterator
        
    
    def get_inplace_step_iterator(self, state, step_profile):
        step_function = step_profile.step_function
        step_type = get_step_type(step_function)
        
        if step_type not in (step_types.InplaceStep,
                             step_types.InplaceStepGenerator):

            raise GarlicSimException("Can't get inplace step iterator for %s, "
                                     "which is a non-inplace step "
                                     "function." % step_function)
            
        inplace_step_iterator_class = step_type.inplace_step_iterator_class

        inplace_step_iterator = inplace_step_iterator_class(
            state_or_history_browser,
            step_profile
        )
        
        return inplace_step_iterator
    
        
