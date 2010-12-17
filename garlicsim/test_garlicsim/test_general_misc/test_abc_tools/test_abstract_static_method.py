import sys

import nose

from garlicsim.general_misc.abc_tools import abstract_static_method
from garlicsim.general_misc.third_party import abc


def test_is_abstract():
    
    if sys.version_info[:2] <= (2, 5):
        raise nose.SkipTest("Python 2.5 and below can't enforce abstract "
                            "methods.")
    
    class A(object):
        __metaclass__ = abc.ABCMeta
        
        @abstract_static_method
        def f():
            pass
        
        
    nose.tools.assert_raises(TypeError, lambda: A())

    
        
def test_override():
    
    class B(object):
        __metaclass__ = abc.ABCMeta
        
        @abstract_static_method
        def f():
            pass
    
    class C(B):
        @staticmethod
        def f():
            return 7
        
    c = C()
    
    assert C.f() == c.f() == 7
    
    