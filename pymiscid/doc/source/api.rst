Contents:

.. toctree::

Service API
====================================

.. autoclass:: pymiscid.service.ServiceCommon
    :members: removeVariableObserver, addVariableObserver

.. autoclass:: pymiscid.service.ServiceBase
    :members:
    :show-inheritance:

.. autoclass:: pymiscid.service.StartedService
    :members: send, stop
    :show-inheritance:

.. autoclass:: pymiscid.service.StoppedService
    :members: 
    :show-inheritance:

.. autoclass:: pymiscid.service.ServiceProxy
    :members: getVariableValue, setVariableValue 
    :show-inheritance:



ServiceFactory API
====================================

.. autoclass:: pymiscid.factory.ServiceFactory
    :members: create, createFromXML, createServiceRepository

Filters
====================================

.. automodule:: filters
    :members:

