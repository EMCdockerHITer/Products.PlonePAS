##############################################################################
#
# PlonePAS - Adapt PluggableAuthService for use in Plone
# Copyright (C) 2005 Enfold Systems, Kapil Thangavelu, et al
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
gruf specific hacks to pas, to make it play well in gruf

in general its not recommended, but its a low risk mechanism for
experimenting with pas flexibility on an existing system.

open question if this mode will be supported at all

$Id$
"""

import sys

from Products.PluggableAuthService.PluggableAuthService import security
from Products.PluggableAuthService.PluggableAuthService import \
          PluggableAuthService, _SWALLOWABLE_PLUGIN_EXCEPTIONS, LOG, BLATHER
#from Products.PluggableAuthService.PluggableAuthService import MANGLE_DELIMITER
from Products.PluggableAuthService.interfaces.plugins \
     import IRoleAssignerPlugin, IAuthenticationPlugin
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.interfaces.plugins import IUserIntrospection

def authenticate(self, name, password, request):

    plugins = self.plugins

    try:
        authenticators = plugins.listPlugins(IAuthenticationPlugin)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        LOG('PluggableAuthService', BLATHER,
            'Plugin listing error',
            error=sys.exc_info())
        authenticators = ()

    credentials = {'login': name,
                   'password': password}

    user_id = None

    for authenticator_id, auth in authenticators:
        try:
            uid_and_name = auth.authenticateCredentials(credentials)

            if uid_and_name == (None,None):
                continue

            user_id, name = uid_and_name

        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            LOG('PluggableAuthService', BLATHER,
                'AuthenticationPlugin %s error' %
                authenticator_id, error=sys.exc_info())
            continue

    if not user_id:
        return

    return self._findUser(plugins, user_id, name, request)

PluggableAuthService.authenticate = authenticate
PluggableAuthService.authenticate__roles__ = ()


#################################
# compat code galore
def userSetGroups(self, id, groupnames):
    plugins = self.plugins

    try:
        groupmanagers = plugins.listPlugins(IGroupManagement)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        LOG('PluggableAuthService', BLATHER,
            'Plugin listing error',
            error=sys.exc_info())
        groupmanagers = ()

    for group in groupnames:
        for gm_id, gm in groupmanagers:
            try:
                if gm.addPrincipalToGroup(id, group):
                    break
            except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                LOG('PluggableAuthService', BLATHER,
                    'AuthenticationPlugin %s error' %
                    gm_id, error=sys.exc_info())

PluggableAuthService.userSetGroups = userSetGroups

def userFolderAddGroup(self, name, roles, groups = (), **kw):
    plugins = self.plugins

    try:
        groupmanagers = plugins.listPlugins(IGroupManagement)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        LOG('PluggableAuthService', BLATHER,
            'Plugin listing error',
            error=sys.exc_info())
        groupmanagers = ()

    for group in groupmanagers:
        for gm_id, gm in groupmanagers:
            try:
                gm.addGroup(name, **kw)
                if roles:
                    gm.setRolesForGroup(name, roles=roles)
                if groups:
                    for group in groups:
                        gm.addPrincipalToGroup(name, group)

            except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                LOG('PluggableAuthService', BLATHER,
                    'AuthenticationPlugin %s error' %
                    gm_id, error=sys.exc_info())

PluggableAuthService.userFolderAddGroup = userFolderAddGroup

#################################
# monkies for the diehard introspection.. all these should die, imho - kt

def getUserIds(self):
    plugins = self.plugins

    try:
        introspectors = plugins.listPlugins(IUserIntrospection)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        LOG('PluggableAuthService', BLATHER,
            'Plugin listing error',
            error=sys.exc_info())
        introspectors = ()

    results = []
    for introspector_id, introspector in introspectors:
        try:
            results.extend(introspector.getUserIds())
        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            LOG('PluggableAuthService', BLATHER,
                    'AuthenticationPlugin %s error' %
                    introspector_id, error=sys.exc_info())

    return results


def getUserNames(self):
    plugins = self.plugins

    try:
        introspectors = plugins.listPlugins(IUserIntrospection)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        LOG('PluggableAuthService', BLATHER,
            'Plugin listing error',
            error=sys.exc_info())
        introspectors = ()

    results = []
    for introspector_id, introspector in introspectors:
        try:
            results.extend(introspector.getUserNames())
        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            LOG('PluggableAuthService', BLATHER,
                    'AuthenticationPlugin %s error' %
                    introspector_id, error=sys.exc_info())

    return results

PluggableAuthService.getUserIds = getUserIds
PluggableAuthService.getUserNames = getUserNames

#################################
# Evil role aquisition blocking

def acquireLocalRoles(self, obj, status = 1):
    """If status is 1, allow acquisition of local roles (regular behaviour).

    If it's 0, prohibit it (it will allow some kind of local role blacklisting).
    """
    mt = getToolByName(self, 'portal_membership')
    if not mt.checkPermission(ModifyPortalContent, obj):
        raise Unauthorized
    # Set local role status
    gruf = getToolByName(self, 'portal_url').getPortalObject().acl_users
    # We perform our own security check
    if not status:
        obj.__ac_local_roles_block__ = 1
    else:
        if getattr(folder, '__ac_local_roles_block__', None):
            folder.__ac_local_roles_block__ = None
    # Reindex the whole stuff.
    obj.reindexObjectSecurity()

PluggableAuthService._acquireLocalRoles = acquireLocalRoles

#################################
# give interested parties some apriori way of noticing pas is a user folder impl
PluggableAuthService.isAUserFolder = 1
