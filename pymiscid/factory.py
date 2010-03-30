#
"""
This is the factory module
"""
import os

from codebench.decorators import unimplemented

import variable
import service
import bonjour

from cstes import OMISCID_DOMAIN


class ServiceFactory(object):
    """
    This object is used to build OMiSCID Service and Service Repository
    """
    service_type = service.StoppedService
    repository_type = service.ServiceRepository
    discoveries = []

    def __init__(self):
        """
        Simple repositories initialization
        """
        self.repositories = {}

    def create(self, name):
        """
        This method create an OMiSCID Service with standard variables.
        """
        srv = self.service_type()
        srv.addVariable("name", "string", "this is the service name",
                            access_type = variable.CONSTANT,
                            value = name)
        srv.addVariable("owner", "string", "this is the service owner",
                            access_type = variable.CONSTANT,
                            value = os.environ['USER'])
        srv.addVariable("class", "string", "this is the service class",
                            access_type = variable.CONSTANT,
                            value = srv.exposed_class_name)
        srv.addVariable("lock", "string", "this is the service lock",
                            access_type = variable.READ,
                            value = "")
        srv.addVariable("peerId", "string", "servicePeerid",
                            access_type = variable.CONSTANT,
                            value = str(srv.peerid))

        return srv

    @unimplemented
    def createFromXML(self, xml):
        """
        Unimplemented yet ...
        """
        pass

    def createServiceRepository(self, domain = OMISCID_DOMAIN):
        """
        This method create a running service repository. The important 
        thing is we only create a service repository per domain.
        """
        if domain not in self.repositories:
            repo = self.repository_type()
            self.repositories[domain] = repo
            discovery = bonjour.BonjourServiceDiscovery(domain)
            discovery.addObserver(repo)
            discovery.run()
            self.discoveries.append(discovery)
        return self.repositories[domain]

    @staticmethod
    def createDomainRepository():
        """
        This method create a running OMiSCID domain repository. 
        (It's just a standard bonjour type discovery with a defined prefix 
        filter).
        """
        discovery = bonjour.BonjourTypeDiscovery('_bip')
        discovery.run()
        return discovery


