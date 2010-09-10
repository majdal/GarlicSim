# Copyright 2009-2010 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

'''This module defines miscellaneous tools.'''

import math
import types

from . import import_tools


def frange(start, finish=None, step=1.):
    '''
    Make a list containing an arithmetic progression of numbers.

    This is an extension of the builtin `range`; It allows using floating point
    numbers.
    '''
    if finish is None:
        finish, start = start, 0.
    else:
        start = float(start)

    count = int(math.ceil(finish - start)/step)
    return (start + n*step for n in range(count))


def shorten_class_address(module_name, class_name):
    '''
    Shorten the address of a class.
    
    This is mostly used in `__repr__` methods of various classes to shorten the
    text and make the final output more conscise. For example, if you have a
    class `garlicsim.asynchronous_crunching.project.Project`, but which is also
    available as `garlicsim.Project`, this function will return
    'garlicsim.Project'.    
    '''
    get_module = lambda module_name: __import__(module_name, fromlist=[''])
    original_module = get_module(module_name)
    original_class = getattr(original_module, class_name)
    
    current_module_name = module_name
    
    last_successful_module_name = current_module_name
    
    while True:
        # Removing the last submodule from the module name:
        current_module_name = '.'.join(current_module_name.split('.')[:-1]) 
        
        if not current_module_name:
            # We've reached the top module and it's successful, can break now.
            break
        
        current_module = get_module(current_module_name)
        
        candidate_class = getattr(current_module, class_name, None)
        
        if candidate_class is original_class:
            last_successful_module_name = current_module_name
        else:
            break
        
    return '.'.join((last_successful_module_name, class_name))





def get_object_from_address(address, parent_object=None):
    if not parent_object:
        if '.' not in address:
            try:
                return eval(address)
            except NameError:
                return __import__(address)   
        else: # '.' in address
            first_object_address, second_object_address = \
                address.rsplit('.', 1)
            first_object = get_object_from_address(first_object_address)
            second_object = get_object_from_address(second_object_address,
                                                    parent_object=first_object)
            return second_object
    
    else: # parent_object is not none
        
        if '.' not in address:
            
            if isinstance(parent_object, types.ModuleType) and \
               hasattr(parent_object, '__path__'):
                
                # It's a package
                import_tools.import_if_exists(
                    '.'.join((parent_object.__name__, address))
                )
                # Not keeping reference, just importing so we could get later
                
            return getattr(parent_object, address)
        
        else: # '.' in address
            first_object_address, second_object_address = \
                address.rsplit('.', 1)
            first_object = get_object_from_address(first_object_address, parent_object)
            second_object = get_object_from_address(second_object_address,
                                                    parent_object=first_object)
            return second_object
    

def get_address_from_object(obj):
    # todo: look for something like this in the community
    assert isinstance(
        obj,
        (
            type, types.FunctionType, types.ModuleType, types.MethodType
        )
    )
    
    if isinstance(obj, types.MethodType):
        address_candidate = '.'.join((obj.__module__, obj.im_class.__name__,
                                      obj.__name__))
        assert get_object_from_address(address_candidate) == obj
        
    else:
        address_candidate = '.'.join((obj.__module__, obj.__name__))
        assert get_object_from_address(address_candidate) is obj
    
    return address_candidate
        

class LazilyEvaluatedConstantProperty(object):
    '''
    A property that is calculated (a) lazily and (b) only once for an object.
    
    Usage:
    
        class MyObject(object):
        
            # ... Regular definitions here
        
            def _get_personality(self):
                print('Calculating personality...')
                time.sleep(5) # Time consuming process that creates personality
                return 'Nice person'
        
            personality = LazilyEvaluatedConstantProperty(_get_personality)
    
    '''
    def __init__(self, getter, name=None):
        '''
        Construct the LEC-property.
        
        You may optionally pass in the name the this property has in the class;
        This will save a bit of processing later.
        '''
        self.getter = getter
        self.our_name = name
        
        
    def __get__(self, obj, our_type=None):

        value = self.getter(obj)
        
        if not self.our_name:
            if not our_type:
                our_type = type(obj)
            (self.our_name,) = (key for (key, value) in 
                                vars(our_type).iteritems()
                                if value is self)
        
        setattr(obj, self.our_name, value)
        
        return value

    
def getted_vars(thing, _getattr=getattr):
    # todo: can make "fallback" option, to use value from original `vars` if get
    # is unsuccessful.
    my_vars = vars(thing)
    return dict((name, _getattr(thing, name)) for name in my_vars.iterkeys())
    

        
if __name__ == '__main__': # todo: move to test suite
    import random
    class A(object):
        def _get_personality(self):
            print(
                "Calculating personality for %s. (Should happen only once.)" % self
            )
            return random.choice(['Angry', 'Happy', 'Sad', 'Excited'])
        personality = LazilyEvaluatedConstantProperty(_get_personality)
    a = A()
    print(a.personality)
    print(a.personality)
    print(a.personality)
    
    a2 = A()
    print(a2.personality)
    print(a2.personality)
    print(a2.personality)
    