#!/usr/bin/env python3
"""
MCP Server Cross-Reference Analysis
Analyzes 46 MCP servers from tools.md against existing implementations
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

def parse_tools_md(file_path: str) -> List[Dict]:
    """Parse tools.md and extract MCP server tools"""
    mcp_servers = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split into tool sections
    tool_sections = content.split('\ntool: ')[1:]  # Skip first empty split
    
    for section in tool_sections:
        lines = section.strip().split('\n')
        tool_name = lines[0]
        
        tool_data = {'name': tool_name}
        
        for line in lines[1:]:
            if line.startswith('description: '):
                tool_data['description'] = line.replace('description: ', '')
            elif line.startswith('type: '):
                tool_data['type'] = line.replace('type: ', '')
            elif line.startswith('purpose: '):
                tool_data['purpose'] = line.replace('purpose: ', '')
            elif line.startswith('url: '):
                tool_data['url'] = line.replace('url: ', '')
            elif line.startswith('dev_needed: '):
                tool_data['dev_needed'] = line.replace('dev_needed: ', '') == 'true'
            elif line.startswith('required: '):
                tool_data['required'] = line.replace('required: ', '') == 'true'
        
        # Only include MCP servers
        if tool_data.get('type') == 'mcp_server':
            mcp_servers.append(tool_data)
    
    return mcp_servers

def check_existing_implementations(devqai_root: str) -> Dict:
    """Check for existing implementations in DevQ.ai projects"""
    implementations = {
        'mcp_servers': [],
        'fastapi_apps': [],
        'related_projects': []
    }
    
    # Check MCP servers directory
    mcp_servers_path = os.path.join(devqai_root, 'mcp', 'mcp-servers')
    if os.path.exists(mcp_servers_path):
        implementations['mcp_servers'] = [
            name for name in os.listdir(mcp_servers_path) 
            if os.path.isdir(os.path.join(mcp_servers_path, name))
        ]
    
    # Check for FastAPI applications
    for root, dirs, files in os.walk(devqai_root):
        # Skip virtual environments and node_modules
        dirs[:] = [d for d in dirs if d not in ['venv', 'node_modules', '__pycache__', '.git']]
        
        for file in files:
            if file == 'main.py':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if 'FastAPI' in content or 'fastapi' in content:
                            implementations['fastapi_apps'].append(file_path)
                except:
                    pass
    
    # Check for related projects (like bayes, darwin, etc.)
    known_projects = ['bayes', 'darwin', 'ptolemies', 'pipeline', 'taskmaster-ai']
    for project in known_projects:
        project_path = os.path.join(devqai_root, project)
        archive_path = os.path.join(devqai_root, 'archive', 'dev', project)
        
        if os.path.exists(project_path):
            implementations['related_projects'].append(f"{project} (active)")
        elif os.path.exists(archive_path):
            implementations['related_projects'].append(f"{project} (archived)")
    
    # Check for TaskMaster MCP server specifically
    taskmaster_mcp_path = os.path.join(devqai_root, 'taskmaster-ai', 'claude-task-master', 'mcp-server')
    if os.path.exists(taskmaster_mcp_path):
        implementations['mcp_servers'].append('task-master-mcp-server')
    
    return implementations

def categorize_servers(mcp_servers: List[Dict], implementations: Dict) -> Dict:
    """Categorize each MCP server by implementation status"""
    categories = {
        'implemented': [],      # ✅ Already implemented
        'partial': [],          # 🏗️ Partially implemented  
        'missing': [],          # ❌ Not implemented
        'external': []          # 🔄 External/Third-party
    }
    
    # Create lookup maps
    existing_mcp = {name.lower().replace('-', '_'): name for name in implementations['mcp_servers']}
    existing_projects = {proj.split(' ')[0].lower(): proj for proj in implementations['related_projects']}
    
    for server in mcp_servers:
        name = server['name']
        name_normalized = name.lower().replace('-', '_')
        
        # Check if already implemented as MCP server
        if name_normalized in existing_mcp:
            location = f"/mcp/mcp-servers/{existing_mcp[name_normalized]}"
            if name_normalized == 'task_master_mcp_server':
                location = "/taskmaster-ai/claude-task-master/mcp-server"
            categories['implemented'].append({
                **server,
                'implementation_type': 'MCP Server',
                'location': location,
                'status': 'Complete MCP implementation'
            })
        
        # Check if related project exists
        elif any(proj_name in name_normalized for proj_name in existing_projects.keys()):
            matching_project = next(proj for proj_name, proj in existing_projects.items() 
                                  if proj_name in name_normalized)
            categories['partial'].append({
                **server,
                'implementation_type': 'Related Project',
                'location': f"/{matching_project.split(' ')[0]}",
                'status': f"Project exists: {matching_project}"
            })
        
        # Check if it's a known external service
        elif server['url'].startswith('https://github.com/modelcontextprotocol/') or \
             server['url'].startswith('https://www.npmjs.com/package/@modelcontextprotocol/'):
            categories['external'].append({
                **server,
                'implementation_type': 'Official MCP',
                'location': server['url'],
                'status': 'Available as official MCP server'
            })
        
        # Check if it's from major providers
        elif any(provider in server['url'] for provider in ['github.com/stripe/', 'github.com/shopify/', 
                                                            'github.com/google/', 'developer.paypal.com']):
            categories['external'].append({
                **server,
                'implementation_type': 'Official Provider',
                'location': server['url'],
                'status': 'Available from official provider'
            })
        
        # Otherwise, it's missing
        else:
            categories['missing'].append({
                **server,
                'implementation_type': 'Not Found',
                'location': 'N/A',
                'status': 'Needs to be implemented'
            })
    
    return categories

def generate_analysis_report(categories: Dict, implementations: Dict) -> str:
    """Generate comprehensive analysis report"""
    
    total_servers = sum(len(cat) for cat in categories.values())
    
    report = f"""
# MCP Server Cross-Reference Analysis Report

## Executive Summary
- **Total MCP Servers Analyzed**: {total_servers}
- **✅ Already Implemented**: {len(categories['implemented'])}
- **🏗️ Partially Implemented**: {len(categories['partial'])}
- **❌ Not Implemented**: {len(categories['missing'])}
- **🔄 External/Third-party**: {len(categories['external'])}

## Current DevQ.ai Infrastructure
- **Existing MCP Servers**: {len(implementations['mcp_servers'])}
- **FastAPI Applications**: {len(implementations['fastapi_apps'])}
- **Related Projects**: {len(implementations['related_projects'])}

---

## Detailed Categorization

### ✅ Already Implemented ({len(categories['implemented'])})
"""
    
    for server in categories['implemented']:
        report += f"""
**{server['name']}**
- Description: {server['description']}
- Location: `{server['location']}`
- Status: {server['status']}
- Purpose: {server['purpose']}
"""
    
    report += f"""
### 🏗️ Partially Implemented ({len(categories['partial'])})
"""
    
    for server in categories['partial']:
        report += f"""
**{server['name']}**
- Description: {server['description']}
- Related Project: `{server['location']}`
- Status: {server['status']}
- Purpose: {server['purpose']}
- Action Needed: Convert existing project to MCP server
"""
    
    report += f"""
### 🔄 External/Third-party Available ({len(categories['external'])})
"""
    
    for server in categories['external']:
        report += f"""
**{server['name']}**
- Description: {server['description']}
- Provider: {server['implementation_type']}
- URL: {server['url']}
- Status: {server['status']}
- Purpose: {server['purpose']}
- Action Needed: Integration and configuration
"""
    
    report += f"""
### ❌ Not Implemented - Needs Development ({len(categories['missing'])})
"""
    
    for server in categories['missing']:
        report += f"""
**{server['name']}**
- Description: {server['description']}
- Purpose: {server['purpose']}
- URL: {server['url']}
- Required: {'Yes' if server.get('required', False) else 'No'}
- Action Needed: Full implementation from scratch
"""
    
    report += f"""
---

## Implementation Recommendations

### Priority 1: Convert Existing Projects to MCP Servers
{len(categories['partial'])} servers can be implemented by converting existing DevQ.ai projects:
"""
    
    for server in categories['partial']:
        report += f"- **{server['name']}**: Use existing `{server['location']}` project\n"
    
    report += f"""
### Priority 2: Integrate External Services
{len(categories['external'])} servers are available from external providers:
"""
    
    for server in categories['external']:
        report += f"- **{server['name']}**: {server['implementation_type']}\n"
    
    report += f"""
### Priority 3: Build from Scratch
{len(categories['missing'])} servers need full implementation:
"""
    
    # Sort missing by required status
    missing_required = [s for s in categories['missing'] if s.get('required', False)]
    missing_optional = [s for s in categories['missing'] if not s.get('required', False)]
    
    if missing_required:
        report += "\n**Required Servers:**\n"
        for server in missing_required:
            report += f"- **{server['name']}**: {server['description']}\n"
    
    if missing_optional:
        report += "\n**Optional Servers:**\n"
        for server in missing_optional:
            report += f"- **{server['name']}**: {server['description']}\n"
    
    report += f"""
---

## Existing DevQ.ai Infrastructure

### MCP Servers Directory (`/mcp/mcp-servers/`)
"""
    
    for server in implementations['mcp_servers']:
        report += f"- `{server}`\n"
    
    report += f"""
### FastAPI Applications
"""
    
    for app in implementations['fastapi_apps']:
        # Make path relative to devqai root
        rel_path = app.replace('/Users/dionedge/devqai/', '')
        report += f"- `{rel_path}`\n"
    
    report += f"""
### Related Projects
"""
    
    for project in implementations['related_projects']:
        report += f"- `{project}`\n"
    
    return report

def main():
    """Main analysis function"""
    devqai_root = '/Users/dionedge/devqai'
    tools_md_path = '/Users/dionedge/devqai/devgen/tools/tools.md'
    
    print("🔍 Parsing tools.md for MCP servers...")
    mcp_servers = parse_tools_md(tools_md_path)
    print(f"Found {len(mcp_servers)} MCP servers")
    
    print("🔍 Checking existing implementations...")
    implementations = check_existing_implementations(devqai_root)
    
    print("🔍 Categorizing servers...")
    categories = categorize_servers(mcp_servers, implementations)
    
    print("📊 Generating analysis report...")
    report = generate_analysis_report(categories, implementations)
    
    # Save report
    report_path = '/Users/dionedge/devqai/devgen/MCP_SERVER_ANALYSIS.md'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Analysis complete! Report saved to: {report_path}")
    
    # Print summary
    total = len(mcp_servers)
    print(f"\n📈 SUMMARY:")
    print(f"✅ Implemented: {len(categories['implemented'])}/{total} ({len(categories['implemented'])/total*100:.1f}%)")
    print(f"🏗️ Partial: {len(categories['partial'])}/{total} ({len(categories['partial'])/total*100:.1f}%)")
    print(f"🔄 External: {len(categories['external'])}/{total} ({len(categories['external'])/total*100:.1f}%)")
    print(f"❌ Missing: {len(categories['missing'])}/{total} ({len(categories['missing'])/total*100:.1f}%)")

if __name__ == "__main__":
    main()