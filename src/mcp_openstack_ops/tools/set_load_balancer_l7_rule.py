"""Tool implementation for set_load_balancer_l7_rule."""

import json
from datetime import datetime
from ..functions import set_load_balancer_l7_rule as _set_load_balancer_l7_rule
from ..mcp_main import (
    conditional_tool,
    logger,
)

@conditional_tool
async def set_load_balancer_l7_rule(
    action: str,
    policy_name_or_id: str = "",
    rule_id: str = "",
    type: str = "PATH",
    compare_type: str = "STARTS_WITH",
    value: str = "",
    key: str = "",
    invert: bool = False,
    admin_state_up: bool = True
) -> str:
    """
    Manage L7 rule operations (create, delete, set, unset, show).
    
    Args:
        action: Action to perform (create, delete, set, unset, show)
        policy_name_or_id: L7 policy name or ID (required for create)
        rule_id: L7 rule ID (required for delete/update operations)
        type: Rule type (PATH, HOST_NAME, HEADER, COOKIE, FILE_TYPE, SSL_CONN_HAS_CERT, SSL_VERIFY_RESULT, SSL_DN_FIELD)
        compare_type: Comparison type (STARTS_WITH, ENDS_WITH, CONTAINS, EQUAL_TO, REGEX)
        value: Rule value to match against
        key: Key for HEADER/COOKIE types
        invert: Whether to invert the rule logic
        admin_state_up: Administrative state
    
    Returns:
        JSON string with operation results
    """
    try:
        logger.info(f"Managing L7 rule with action: {action}")
        
        kwargs = {
            'policy_name_or_id': policy_name_or_id,
            'rule_id': rule_id,
            'type': type,
            'compare_type': compare_type,
            'value': value,
            'key': key if key else None,
            'invert': invert,
            'admin_state_up': admin_state_up
        }
        
        result = _set_load_balancer_l7_rule(action, **kwargs)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        return json.dumps(response, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage L7 rule - {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "success": False
        }, indent=2)
