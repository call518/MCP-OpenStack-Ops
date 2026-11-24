import os
import logging
from typing import Dict, List, Any, Optional
from openstack import connection
from dotenv import load_dotenv
from datetime import datetime, timezone

# Import connection management from separate module
from .connection import get_openstack_connection, reset_connection_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _service_zone(service, default='unknown'):
    """Return a Nova/Cinder service zone.

    openstacksdk maps the API's ``zone`` field to ``availability_zone``;
    ``service.zone`` raises AttributeError on real SDK resources.
    """
    return (getattr(service, 'availability_zone', None)
            or getattr(service, 'zone', None) or default)

def _api_probe(binary: str, service_type: str, probe) -> Dict[str, Any]:
    """Run a one-item list against a service API and describe the result.

    A probe row is not a service record: it only says whether the API
    answered, so host and updated_at are null and checked_at is UTC.
    """
    row = {
        'binary': binary, 'service_type': service_type, 'check': 'api_probe',
        'host': None, 'status': None, 'updated_at': None,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }
    try:
        probe()
        row['state'] = 'up'
    except Exception as e:
        logger.warning(f"{binary} API probe failed: {e}")
        row['state'] = 'unknown'
        row['error'] = str(e)
    return row


def _adapter_probe(conn, service_type: str, path: str):
    """Return a probe that GETs path from a service without an SDK proxy."""
    from keystoneauth1.adapter import Adapter

    def probe():
        Adapter(
            session=conn.session, service_type=service_type,
            interface=conn.config.get_interface(),
            region_name=conn.config.region_name,
        ).get(path, raise_exc=True)
    return probe


def _in_catalog(conn, service_type: str) -> bool:
    """Whether the service catalog has an endpoint for service_type.

    openstacksdk's has_service() is False for types without an SDK proxy,
    such as alarming and metric, even when the catalog lists them.
    """
    try:
        return bool(conn.session.get_endpoint(
            service_type=service_type, interface=conn.config.get_interface(),
            region_name=conn.config.region_name))
    except Exception:
        return False


def _heat_engine_services(conn) -> List[Dict[str, Any]]:
    """Read heat-engine records from Heat's service API (usually admin-only)."""
    try:
        response = conn.orchestration.get('/services')
        response.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to get Heat engine services: {e}")
        return [{
            'binary': 'heat-engine', 'service_type': 'orchestration',
            'status': 'unknown', 'state': 'unknown', 'error': str(e),
        }]
    return [{
        'binary': service.get('binary'),
        'host': service.get('host'),
        # Heat has no enable flag; its status is the engine's liveness.
        'status': None,
        'state': service.get('status'),
        'zone': None,
        'updated_at': service.get('updated_at'),
        'engine_id': service.get('engine_id'),
        'service_type': 'orchestration',
    } for service in response.json().get('services', [])]


def get_service_status() -> List[Dict[str, Any]]:
    """
    Report Nova and Cinder services, Neutron agents and Heat engines from
    their service APIs, and probe the Glance and Heat APIs and, when they are
    in the catalog, the Octavia, Barbican, Aodh and Gnocchi APIs.

    Returns:
        List of service rows; API probe rows carry check="api_probe".

    Raises:
        Exception: when the connection itself fails; no placeholder rows
        are returned in that case.
    """
    conn = get_openstack_connection()
    services = []

    # Nova compute services
    try:
        for service in conn.compute.services():
            services.append({
                'binary': service.binary,
                'host': service.host,
                'status': service.status,
                'state': service.state,
                'zone': _service_zone(service),
                'updated_at': getattr(service, 'updated_at', None),
                'disabled_reason': getattr(service, 'disabled_reason', None),
                'service_type': 'compute'
            })
    except Exception as e:
        logger.warning(f"Failed to get compute services: {e}")
        services.append({
            'binary': 'nova-compute', 'service_type': 'compute',
            'status': 'unknown', 'state': 'unknown', 'error': str(e),
        })

    # Neutron agents
    try:
        for agent in conn.network.agents():
            services.append({
                'binary': agent.binary,
                'host': agent.host,
                'status': ('unknown' if agent.is_admin_state_up is None else
                           'enabled' if agent.is_admin_state_up else 'disabled'),
                'state': ('unknown' if agent.is_alive is None else
                          'up' if agent.is_alive else 'down'),
                'zone': getattr(agent, 'availability_zone', None),
                'updated_at': getattr(agent, 'last_heartbeat_at', None),
                'agent_type': agent.agent_type,
                'service_type': 'network'
            })
    except Exception as e:
        logger.warning(f"Failed to get network agents: {e}")
        services.append({
            'binary': 'neutron-agent', 'service_type': 'network',
            'status': 'unknown', 'state': 'unknown', 'error': str(e),
        })

    # Cinder services
    try:
        for service in conn.volume.services():
            services.append({
                'binary': service.binary,
                'host': service.host,
                'status': service.status,
                'state': service.state,
                'zone': _service_zone(service),
                'updated_at': getattr(service, 'updated_at', None),
                'disabled_reason': getattr(service, 'disabled_reason', None),
                'service_type': 'volume'
            })
    except Exception as e:
        logger.warning(f"Failed to get volume services: {e}")
        services.append({
            'binary': 'cinder-volume', 'service_type': 'volume',
            'status': 'unknown', 'state': 'unknown', 'error': str(e),
        })

    # Heat engines (service records) and API probes for services without a
    # service list. Glance and Heat are always probed; the others only when
    # the catalog has them.
    services.append(_api_probe(
        'glance-api', 'image', lambda: list(conn.image.images(limit=1))))
    services.append(_api_probe(
        'heat-api', 'orchestration', lambda: list(conn.orchestration.stacks(limit=1))))
    services.extend(_heat_engine_services(conn))
    optional = (
        ('octavia-api', 'load-balancer',
         lambda: list(conn.load_balancer.providers())),
        ('barbican-api', 'key-manager',
         lambda: next(iter(conn.key_manager.secrets(limit=1)), None)),
        ('aodh-api', 'alarming',
         _adapter_probe(conn, 'alarming', '/v2/alarms?limit=1')),
        ('gnocchi-api', 'metric',
         _adapter_probe(conn, 'metric', '/v1/resource/generic?limit=1')),
    )
    for binary, service_type, probe in optional:
        if _in_catalog(conn, service_type):
            services.append(_api_probe(binary, service_type, probe))

    return services

# =============================================================================
# Compute (Nova) Functions - Enhanced
# =============================================================================
# Compute (Nova) Functions - Enhanced
# =============================================================================

# Compute functions are now imported from services.compute module
# All compute-related functionality has been modularized


# =============================================================================
# Image Service (Glance) Functions - Enhanced
# =============================================================================

def set_identity_groups(action: str, group_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack identity groups (list, show, create, delete, update)
    
    Args:
        action: Action to perform (list, show, create, delete, update)
        group_name: Name or ID of the group
        **kwargs: Additional parameters
    
    Returns:
        Result of the identity group management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            groups = []
            try:
                for group in conn.identity.groups():
                    groups.append({
                        'id': group.id,
                        'name': group.name,
                        'description': getattr(group, 'description', 'N/A'),
                        'domain_id': getattr(group, 'domain_id', 'N/A'),
                        'created_at': str(getattr(group, 'created_at', 'N/A')),
                        'updated_at': str(getattr(group, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Identity groups not accessible: {str(e)}',
                    'groups': []
                }
            return {
                'success': True,
                'groups': groups,
                'count': len(groups)
            }
            
        elif action.lower() == 'create':
            if not group_name:
                return {
                    'success': False,
                    'message': 'group_name is required for create action'
                }
                
            description = kwargs.get('description', f'Group created via MCP: {group_name}')
            domain_id = kwargs.get('domain_id', 'default')
            
            try:
                group = conn.identity.create_group(
                    name=group_name,
                    description=description,
                    domain_id=domain_id
                )
                return {
                    'success': True,
                    'message': f'Group "{group_name}" created successfully',
                    'group_id': group.id,
                    'domain_id': domain_id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create group: {str(e)}'
                }
        
        elif action.lower() in {'show', 'delete', 'update'}:
            if not group_name:
                raise ValueError('group_name is required')
            group = conn.identity.find_group(
                group_name, ignore_missing=False, domain_id=kwargs.get('domain_id',
                    'default'),
            )
            if action.lower() == 'delete':
                conn.identity.delete_group(group, ignore_missing=False)
                return {'success': True, 'message': 'Identity group deletion accepted'}
            if action.lower() == 'update':
                group = conn.identity.update_group(group,
                    description=kwargs.get('description', ''))
            return {'success': True, 'group': group.to_dict()}

        else:
            return {
                'success': False,
                'message': f'Unknown action "{
                    action}". Supported: list, create, show, update, delete'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage identity group: {e}")
        return {
            'success': False,
            'message': f'Failed to manage identity group: {str(e)}',
            'error': str(e)
        }


def set_roles(action: str, role_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Manage OpenStack roles (list, show, create, delete, assign, unassign)
    
    Args:
        action: Action to perform (list, show, create, delete, assign, unassign)
        role_name: Name or ID of the role
        **kwargs: Additional parameters
    
    Returns:
        Result of the role management operation
    """
    try:
        conn = get_openstack_connection()
        
        if action.lower() == 'list':
            roles = []
            try:
                for role in conn.identity.roles():
                    roles.append({
                        'id': role.id,
                        'name': role.name,
                        'description': getattr(role, 'description', 'N/A'),
                        'domain_id': getattr(role, 'domain_id', None),
                        'created_at': str(getattr(role, 'created_at', 'N/A')),
                        'updated_at': str(getattr(role, 'updated_at', 'N/A'))
                    })
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Roles not accessible: {str(e)}',
                    'roles': []
                }
            return {
                'success': True,
                'roles': roles,
                'count': len(roles)
            }
            
        elif action.lower() == 'create':
            if not role_name:
                return {
                    'success': False,
                    'message': 'role_name is required for create action'
                }
                
            description = kwargs.get('description', f'Role created via MCP: {role_name}')
            domain_id = kwargs.get('domain_id', None)
            
            try:
                role = conn.identity.create_role(
                    name=role_name,
                    description=description,
                    domain_id=domain_id
                )
                return {
                    'success': True,
                    'message': f'Role "{role_name}" created successfully',
                    'role_id': role.id,
                    'domain_id': domain_id
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create role: {str(e)}'
                }
        
        else:
            return {
                'success': False,
                'message': f'Unknown action "{action}". Supported: list, create'
            }
            
    except Exception as e:
        logger.error(f"Failed to manage role: {e}")
        return {
            'success': False,
            'message': f'Failed to manage role: {str(e)}',
            'error': str(e)
        }


def get_services() -> Dict[str, Any]:
    """
    List the Keystone service catalog (like 'openstack service list').

    Returns:
        Services with id, name, type, description and enabled, or a failure
    """
    try:
        conn = get_openstack_connection()
        services = []
        try:
            for service in conn.identity.services():
                services.append({
                    'id': service.id,
                    'name': service.name,
                    'type': service.type,
                    'description': getattr(service, 'description', 'N/A'),
                    'enabled': getattr(service, 'is_enabled', True),
                    'created_at': str(getattr(service, 'created_at', 'N/A')),
                    'updated_at': str(getattr(service, 'updated_at', 'N/A'))
                })
        except Exception as e:
            return {
                'success': False,
                'message': f'Services not accessible: {str(e)}',
                'services': []
            }
        return {
            'success': True,
            'services': services,
            'count': len(services)
        }

    except Exception as e:
        logger.error(f"Failed to list services: {e}")
        return {
            'success': False,
            'message': f'Failed to list services: {str(e)}',
            'error': str(e)
        }


from .services.alarms import set_alarms
from .services.gnocchi import (
    get_gnocchi_aggregates,
    get_gnocchi_measures,
    get_gnocchi_metrics,
    get_gnocchi_resources,
    get_gnocchi_service_info,
)


def get_compute_agents(
    agent_id: str = None,
    host: str = None
) -> Dict[str, Any]:
    """
    List Nova compute services with hypervisors, or show one compute service.

    Args:
        agent_id: ID of one compute service to show
        host: Host name that filters the list (services and hypervisors)

    Returns:
        Compute agent information, or a failure with the error
    """
    try:
        conn = get_openstack_connection()

        if agent_id:
            # The compute proxy has no get_service(); look the
            # service up from the os-services listing instead.
            service = next(
                (svc for svc in conn.compute.services()
                 if str(svc.id) == str(agent_id)),
                None,
            )
            if service is None:
                return {
                    'success': False,
                    'message': f'Compute service "{agent_id}" not found'
                }
            return {
                'success': True,
                'agent_details': {
                    'id': service.id,
                    'binary': service.binary,
                    'host': service.host,
                    'zone': _service_zone(service),
                    'status': service.status,
                    'state': service.state,
                    'updated_at': service.updated_at,
                    'disabled_reason': getattr(service, 'disabled_reason', None)
                }
            }

        # A failed service listing is reported as a failure, not as an
        # empty list of services.
        agents = []
        for service in conn.compute.services():
            if not host or service.host == host:
                agents.append({
                    'id': service.id,
                    'binary': service.binary,
                    'host': service.host,
                    'zone': _service_zone(service),
                    'status': service.status,
                    'state': service.state,
                    'updated_at': service.updated_at,
                    'disabled_reason': getattr(service, 'disabled_reason', None)
                })

        # Get hypervisor information
        try:
            hypervisors = []
            from .services.monitoring import _hypervisor_capacity
            for hypervisor in conn.compute.hypervisors(details=True):
                if not host or hypervisor.name == host:
                    # SDK names are memory_size/local_disk_size; Nova
                    # 2.88+ omits capacity fields, which stay None.
                    hypervisors.append({
                        'id': hypervisor.id,
                        'name': hypervisor.name,
                        'status': hypervisor.status,
                        'state': hypervisor.state,
                        **_hypervisor_capacity(hypervisor),
                    })
        except Exception as e:
            logger.warning(f"Could not get hypervisor information: {e}")
            return {
                'success': True,
                'compute_services': agents,
                'hypervisors_error': str(e),
                'count': {'services': len(agents)}
            }
        return {
            'success': True,
            'compute_services': agents,
            'hypervisors': hypervisors,
            'count': {
                'services': len(agents),
                'hypervisors': len(hypervisors)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get compute agents: {e}")
        return {
            'success': False,
            'message': f'Failed to get compute agents: {str(e)}',
            'error': str(e)
        }


# =============================================================================
# OCTAVIA (LOAD BALANCER) FUNCTIONS - IMPORTED FROM MODULAR SERVICES
# =============================================================================

# Load balancer functions are now modularized in services.load_balancer
# Import compute functions from services
from .services.compute import (
    get_instance_details,
    get_instance_by_name,
    get_instance_by_id,
    search_instances,
    get_instances_by_status,
    set_instance,
    get_flavor_list,
    get_server_events,
    get_server_groups,
    set_server_group,
    set_flavor,
    set_server_network,
    set_server_floating_ip,
    set_server_fixed_ip,
    set_server_security_group,
    set_server_migration,
    set_server_properties,
    create_server_backup,
    create_server_dump
)

# Import network functions from services
from .services.network import (
    get_network_details,
    get_security_groups,
    get_floating_ips,
    get_floating_ip_pools,
    set_floating_ip,
    set_floating_ip_port_forwarding,
    get_routers,
    set_networks,
    set_network_ports,
    set_subnets
)

# Import storage functions from services
from .services.storage import (
    get_volume_list,
    set_volume,
    get_volume_types,
    get_volume_snapshots,
    set_snapshot,
    set_volume_backups,
    set_volume_groups,
    set_volume_qos,
    get_server_volumes,
    set_server_volume
)

# Import identity functions from services
from .services.identity import (
    get_project_info,
    get_user_list,
    get_role_assignments,
    get_keypair_list,
    set_keypair,
    get_project_details,
    set_project,
    set_domains
)

# Import image functions from services
from .services.image import (
    get_image_list,
    get_image_detail_list,
    set_image,
    set_image_members,
    set_image_metadata,
    set_image_visibility
)

# Import monitoring functions from services  
from .services.monitoring import (
    get_resource_monitoring,
    get_usage_statistics,
    get_quota,
    get_hypervisor_details,
    get_availability_zones,
    set_quota
)

# Import orchestration functions from services
from .services.orchestration import (
    get_heat_stacks,
    set_heat_stack
)

from .services.load_balancer import (
    # Core operations
    get_load_balancer_list,
    get_load_balancer_details, 
    set_load_balancer,
    
    # Listener operations
    get_load_balancer_listeners,
    set_load_balancer_listener,
    
    # Pool operations
    get_load_balancer_pools,
    set_load_balancer_pool,
    get_load_balancer_pool_members,
    set_load_balancer_pool_member,
    
    # Health monitor operations
    get_load_balancer_health_monitors,
    set_load_balancer_health_monitor,
    
    # L7 policy operations
    get_load_balancer_l7_policies,
    set_load_balancer_l7_policy,
    get_load_balancer_l7_rules,
    set_load_balancer_l7_rule,
    
    # Management operations
    get_load_balancer_availability_zones,
    set_load_balancer_availability_zone,
    get_load_balancer_flavors,
    set_load_balancer_flavor,
    get_load_balancer_providers,
    get_load_balancer_quotas,
    set_load_balancer_quota,
    
    # Amphora operations
    get_load_balancer_amphorae,
    set_load_balancer_amphora,
    _set_load_balancer_amphora
)


# =============================================================================
# Additional network management functions
# =============================================================================
from .services.network import set_network_qos_policies, set_network_agents
