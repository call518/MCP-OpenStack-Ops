"""Tool implementation for set_heat_stack."""

import json
from datetime import datetime
from ..functions import set_heat_stack as _set_heat_stack
from ..mcp_main import (
    conditional_tool,
    handle_operation_result,
    logger,
)

@conditional_tool
async def set_heat_stack(stack_names: str, action: str, template: str = "",
                         parameters: str = "", files: str = "", environment: str = "",
                         timeout_mins: int = 0, existing: bool = False) -> str:
    """
    Manage Heat orchestration stacks (create, delete, update, validate).
    Supports both single stack and bulk operations.

    Functions:
    - Validate a template, with its files and environment, before create/update
    - Create new stacks from Heat templates
    - Delete existing stacks
    - Update stack configurations and parameters
    - Bulk operations: Apply action to multiple stacks at once

    Use when user requests Heat stack management, infrastructure orchestration, or template deployment tasks.

    Template rules:
    - A template that uses another template as a resource type (provider or
      nested template, e.g. type: member.yaml, or a resource_registry entry)
      needs that template's content in files, keyed by the same name.
    - Do not use OS::Heat::Stack as the member of OS::Heat::AutoScalingGroup
      or ResourceGroup. Scaling triggered by an Aodh alarm runs with a trust,
      and creating a top-level stack from a trust fails with HTTP 403 because
      Keystone forbids trust redelegation. Use a nested template in files.
    - create, update and delete are asynchronous; confirm the final state
      with get_heat_stacks or get_heat_stack_details.

    Args:
        stack_names: Name(s) of stacks to manage. Support formats:
                    - Single: "stack1"
                    - Multiple: "stack1,stack2,stack3" or "stack1, stack2, stack3"
                    - List format: '["stack1", "stack2", "stack3"]'
                    For validate the name is only a label.
        action: Action to perform (create, delete, update, validate)
        template: Heat template content (YAML or JSON). Required for create,
            validate, and update unless existing is true.
        parameters: Stack parameters in JSON format (optional)
        files: JSON object mapping each referenced file name to its content,
            like 'openstack stack create -t' collects (optional). Content only;
            the server does not read local paths or URLs.
        environment: Environment content (JSON, or YAML text) with
            parameters, parameter_defaults or resource_registry (optional)
        timeout_mins: Stack timeout in minutes for create/update; 0 keeps
            Heat's default (create) or the current value (update with existing)
        existing: For update only. False (default) replaces the stack
            definition like 'openstack stack update': parameters, files and
            environment that are not passed revert to template defaults or are
            dropped, which can replace resources. True keeps the stored
            template, parameters, files and environment and changes only what
            is passed, like 'openstack stack update --existing'. Use true to
            change a subset, for example one parameter.

    Returns:
        Result of stack management operation in JSON format.
        For bulk operations, returns summary of successes and failures.
    """
    
    try:
        if not stack_names or not stack_names.strip():
            return "Error: Stack name(s) are required"
            
        names_str = stack_names.strip()
        
        # Handle JSON list format: ["name1", "name2"]
        if names_str.startswith('[') and names_str.endswith(']'):
            try:
                name_list = json.loads(names_str)
                if not isinstance(name_list, list):
                    return "Error: Invalid JSON list format for stack names"
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for stack names"
        else:
            # Handle comma-separated format: "name1,name2" or "name1, name2"
            name_list = [name.strip() for name in names_str.split(',')]
        
        # Remove empty strings
        name_list = [name for name in name_list if name]
        
        if not name_list:
            return "Error: No valid stack names provided"
        
        kwargs = {}
        if template.strip():
            try:
                kwargs['template'] = json.loads(template.strip())
            except json.JSONDecodeError:
                # If not JSON, treat as YAML or plain text template
                kwargs['template'] = template.strip()
        
        if parameters.strip():
            try:
                kwargs['parameters'] = json.loads(parameters.strip())
            except json.JSONDecodeError:
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "error": "Invalid JSON format for parameters",
                    "message": "Parameters must be valid JSON format"
                }, indent=2, ensure_ascii=False)

        if files.strip():
            try:
                files_map = json.loads(files.strip())
            except json.JSONDecodeError:
                files_map = None
            if not isinstance(files_map, dict) or not all(
                    isinstance(v, str) for v in files_map.values()):
                return json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "error": "Invalid files format",
                    "message": "files must be a JSON object of file name to content string"
                }, indent=2, ensure_ascii=False)
            kwargs['files'] = files_map

        if environment.strip():
            try:
                kwargs['environment'] = json.loads(environment.strip())
            except json.JSONDecodeError:
                # Heat parses a YAML environment string itself.
                kwargs['environment'] = environment.strip()

        if timeout_mins < 0:
            return "Error: timeout_mins must be 0 or greater"
        if timeout_mins:
            kwargs['timeout_mins'] = timeout_mins
        if existing:
            kwargs['existing'] = True

        # Handle single stack (backward compatibility)
        if len(name_list) == 1:
            logger.info(f"Managing stack '{name_list[0]}' with action '{action}'")
            result_data = _set_heat_stack(name_list[0], action, **kwargs)
            
            return handle_operation_result(
                result_data,
                "Heat Stack Management",
                {
                    "Action": action,
                    "Stack Name": name_list[0],
                    "Template": "Provided" if template.strip() else "Not provided",
                    "Parameters": "Provided" if parameters.strip() else "Not provided",
                    "Files": ", ".join(kwargs.get('files', {})) or "Not provided",
                    "Environment": "Provided" if environment.strip() else "Not provided"
                }
            )
        
        # Handle bulk operations (multiple stacks)
        else:
            logger.info(f"Managing {len(name_list)} stacks with action '{action}': {name_list}")
            results = []
            successes = []
            failures = []
            
            for stack_name in name_list:
                try:
                    result = _set_heat_stack(stack_name.strip(), action, **kwargs)
                    
                    # Check if result indicates success or failure
                    if isinstance(result, dict):
                        if result.get('success', False):
                            successes.append(stack_name)
                            results.append(f"✓ {stack_name}: {result.get('message', 'Success')}")
                        else:
                            failures.append(stack_name)
                            results.append(f"✗ {stack_name}: {result.get('error', 'Unknown error')}")
                    elif isinstance(result, str):
                        # For string results, check if it contains error indicators
                        if 'error' in result.lower() or 'failed' in result.lower():
                            failures.append(stack_name)
                            results.append(f"✗ {stack_name}: {result}")
                        else:
                            successes.append(stack_name)
                            results.append(f"✓ {stack_name}: {result}")
                    else:
                        successes.append(stack_name)
                        results.append(f"✓ {stack_name}: Operation completed")
                        
                except Exception as e:
                    failures.append(stack_name)
                    results.append(f"✗ {stack_name}: {str(e)}")
            
            # Prepare summary
            summary_parts = [
                f"Bulk Heat Stack Management - Action: {action}",
                f"Total stacks: {len(name_list)}",
                f"Successes: {len(successes)}",
                f"Failures: {len(failures)}"
            ]
            
            if successes:
                summary_parts.append(f"Successful stacks: {', '.join(successes)}")
            if failures:
                summary_parts.append(f"Failed stacks: {', '.join(failures)}")
                
            summary_parts.append("\nDetailed Results:")
            summary_parts.extend(results)
            
            return "\n".join(summary_parts)
        
    except Exception as e:
        error_msg = f"Error: Failed to manage stack(s) '{stack_names}' - {str(e)}"
        logger.error(error_msg)
        return error_msg
