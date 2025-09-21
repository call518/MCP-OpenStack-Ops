"""
OpenStack MCP Services Module

This package contains modularized OpenStack service functions organized by service type.
Each module focuses on a specific OpenStack service area for better maintainability.
"""

# Core connection and cluster management
from .core import (
    get_service_status
)

# Compute service functions
from .compute import (
    get_instance_details,
    get_instance_by_name,
    get_instance_by_id,
    search_instances,
    get_instances_by_status,
    set_instance,
    get_flavor_list,
    set_flavor,
    get_server_events,
    get_server_groups,
    set_server_group
)

# Storage service functions
from .storage import (
    set_volume,
    get_volume_list,
    get_volume_types,
    get_volume_snapshots,
    set_snapshot,
    set_volume_backups,
    set_volume_groups,
    set_volume_qos
)

# Network service functions
from .network import (
    get_network_details,
    get_security_groups,
    get_floating_ips,
    set_floating_ip,
    get_routers,
    set_network_ports,
    set_subnets
)

# Load balancer service functions - TODO: Create load_balancer module
# from .load_balancer import (
#     get_load_balancer_list,
#     get_load_balancer_details,
#     get_load_balancer_status,
#     set_load_balancer,
#     get_load_balancer_listeners,
#     set_load_balancer_listener,
#     get_load_balancer_pools,
#     set_load_balancer_pool,
#     get_load_balancer_members,
#     get_load_balancer_pool_members,
#     set_load_balancer_member,
#     set_load_balancer_pool_member,
#     get_load_balancer_health_monitors,
#     set_load_balancer_health_monitor,
#     get_load_balancer_l7_policies,
#     set_load_balancer_l7_policy,
#     get_load_balancer_l7_rules,
#     set_load_balancer_l7_rule,
#     get_load_balancer_amphorae,
#     set_load_balancer_amphora,
#     _set_load_balancer_amphora,
#     get_load_balancer_availability_zones,
#     set_load_balancer_availability_zone,
#     get_load_balancer_flavors,
#     set_load_balancer_flavor,
#     get_load_balancer_flavor_profiles,
#     set_load_balancer_flavor_profile,
#     get_load_balancer_providers,
#     get_load_balancer_quotas,
#     set_load_balancer_quota
# )

# Identity service functions
from .identity import (
    get_project_info,
    get_project_details,
    set_project,
    get_user_list,
    get_role_assignments,
    get_keypair_list,
    set_keypair
)

# Orchestration service functions
from .orchestration import (
    get_heat_stacks,
    set_heat_stack
)

# Image service functions
from .image import (
    get_image_list,
    get_image_detail_list,
    set_image,
    set_image_members,
    set_image_metadata,
    set_image_visibility
)

# Monitoring and resource management
from .monitoring import (
    get_resource_monitoring,
    get_usage_statistics,
    get_quota,
    set_quota,
    get_compute_quota_usage,
    get_hypervisor_details,
    get_availability_zones
)

# Storage service functions  
from .storage import (
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

__all__ = [
    # Core
    'get_openstack_connection',
    'reset_connection_cache',
    'get_service_status',
    
    # Compute
    'get_instance_details',
    'get_instance_by_name',
    'get_instance_by_id',
    'search_instances',
    'get_instances_by_status',
    'set_instance',
    'get_server_events',
    'get_server_groups',
    'set_server_group',
    'get_hypervisor_details',
    'get_availability_zones',
    'get_flavor_list',
    'set_flavor',
    'get_server_volumes',
    'set_server_volume',
    
    # Storage
    'set_volume',
    'get_volume_list',
    'get_volume_types',
    'get_volume_snapshots',
    'set_snapshot',
    'set_volume_backups',
    'set_volume_groups',
    'set_volume_qos',
    
    # Network
    'get_network_details',
    'get_security_groups',
    'get_floating_ips',
    'set_floating_ip',
    'get_routers',
    'set_network_ports',
    'set_subnets',
    
    # Load Balancer
    'get_load_balancer_list',
    'get_load_balancer_details',
    'get_load_balancer_status',
    'set_load_balancer',
    'get_load_balancer_listeners',
    'set_load_balancer_listener',
    'get_load_balancer_pools',
    'set_load_balancer_pool',
    'get_load_balancer_members',
    'get_load_balancer_pool_members',
    'set_load_balancer_member',
    'set_load_balancer_pool_member',
    'get_load_balancer_health_monitors',
    'set_load_balancer_health_monitor',
    'get_load_balancer_l7_policies',
    'set_load_balancer_l7_policy',
    'get_load_balancer_l7_rules',
    'set_load_balancer_l7_rule',
    'get_load_balancer_amphorae',
    'set_load_balancer_amphora',
    '_set_load_balancer_amphora',
    'get_load_balancer_availability_zones',
    'set_load_balancer_availability_zone',
    'get_load_balancer_flavors',
    'set_load_balancer_flavor',
    'get_load_balancer_flavor_profiles',
    'set_load_balancer_flavor_profile',
    'get_load_balancer_providers',
    'get_load_balancer_quotas',
    'set_load_balancer_quota',
    
    # Identity
    'get_project_info',
    'get_project_details',
    'set_project',
    'get_user_list',
    'get_role_assignments',
    'get_keypair_list',
    'set_keypair',
    
    # Orchestration
    'get_heat_stacks',
    'set_heat_stack',
    
    # Image
    'get_image_list',
    'get_image_detail_list',
    'set_image',
    'set_image_members',
    'set_image_metadata',
    'set_image_visibility',
    
    # Monitoring
    'get_resource_monitoring',
    'get_usage_statistics',
    'get_quota',
    'set_quota',
    'get_compute_quota_usage',
    'monitor_resources'
]