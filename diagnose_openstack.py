#!/usr/bin/env python3
"""
OpenStack 권한 및 API 접근 진단 스크립트
"""
import os
from dotenv import load_dotenv
from openstack import connection
import json

def diagnose_openstack_access():
    load_dotenv()
    
    print("=== OpenStack API 접근 진단 ===")
    print(f"사용자: {os.environ.get('OS_USERNAME')}")
    print(f"프로젝트: {os.environ.get('OS_PROJECT_NAME')}")
    print(f"인증 URL: {os.environ.get('OS_AUTH_URL')}")
    print()
    
    try:
        conn = connection.Connection(
            auth_url=os.environ.get('OS_AUTH_URL'),
            project_name=os.environ.get('OS_PROJECT_NAME'),
            username=os.environ.get('OS_USERNAME'),
            password=os.environ.get('OS_PASSWORD'),
            user_domain_name=os.environ.get('OS_USER_DOMAIN_NAME', 'default'),
            project_domain_name=os.environ.get('OS_PROJECT_DOMAIN_NAME', 'default'),
        )
        
        print("✅ OpenStack 연결 성공")
        
        # 1. 현재 사용자 정보
        try:
            token = conn.identity.get_token()
            print(f"✅ 토큰 획득 성공")
            
            # 사용자 역할 확인
            user_id = conn.current_user_id
            project_id = conn.current_project_id
            
            roles = list(conn.identity.role_assignments.list(user=user_id, project=project_id))
            print(f"현재 사용자 역할: {len(roles)}개")
            
            for assignment in roles:
                role_id = assignment.role['id']
                role = conn.identity.get_role(role_id)
                print(f"  - {role.name}")
                
        except Exception as e:
            print(f"❌ 사용자 정보 조회 실패: {e}")
        
        print()
        
        # 2. Hypervisor 정보 (admin 권한 필요)
        print("--- Hypervisor 정보 조회 (admin 권한 필요) ---")
        try:
            hypervisors = list(conn.compute.hypervisors(details=True))
            print(f"✅ Hypervisor 조회 성공: {len(hypervisors)}개")
            
            for hyp in hypervisors:
                print(f"Hypervisor ID: {hyp.id}")
                print(f"  이름: {getattr(hyp, 'hypervisor_hostname', 'N/A')}")
                print(f"  상태: {getattr(hyp, 'status', 'N/A')}/{getattr(hyp, 'state', 'N/A')}")
                print(f"  vCPUs: {getattr(hyp, 'vcpus_used', 'N/A')}/{getattr(hyp, 'vcpus', 'N/A')}")
                print(f"  메모리: {getattr(hyp, 'memory_mb_used', 'N/A')}/{getattr(hyp, 'memory_mb', 'N/A')} MB")
                print(f"  실행 중 VM: {getattr(hyp, 'running_vms', 'N/A')}")
                print(f"  타입: {getattr(hyp, 'hypervisor_type', 'N/A')}")
                print()
                
        except Exception as e:
            print(f"❌ Hypervisor 조회 실패: {e}")
            print("   → admin 권한이 필요할 수 있습니다")
        
        print()
        
        # 3. 프로젝트 내 인스턴스 조회 (일반 사용자 권한으로 가능)
        print("--- 프로젝트 인스턴스 조회 (일반 사용자 권한) ---")
        try:
            servers = list(conn.compute.servers(details=True))
            print(f"✅ 인스턴스 조회 성공: {len(servers)}개")
            
            total_vcpus_used = 0
            total_memory_used = 0
            
            for server in servers:
                flavor = conn.compute.get_flavor(server.flavor['id'])
                total_vcpus_used += flavor.vcpus
                total_memory_used += flavor.ram
                
                print(f"인스턴스: {server.name}")
                print(f"  상태: {server.status}")
                print(f"  Flavor vCPUs: {flavor.vcpus}")
                print(f"  Flavor RAM: {flavor.ram} MB")
                print(f"  호스트: {getattr(server, 'OS-EXT-SRV-ATTR:host', 'N/A')}")
            
            print(f"\n📊 프로젝트 리소스 사용량:")
            print(f"  총 vCPUs 사용: {total_vcpus_used}")
            print(f"  총 메모리 사용: {total_memory_used} MB")
                
        except Exception as e:
            print(f"❌ 인스턴스 조회 실패: {e}")
        
        print()
        
        # 4. 쿼터 정보
        print("--- 프로젝트 쿼터 조회 ---")
        try:
            project_id = conn.current_project_id
            quotas = conn.compute.get_quota_set(project_id)
            
            print(f"✅ 쿼터 조회 성공:")
            print(f"  인스턴스: {getattr(quotas, 'instances', 'N/A')}")
            print(f"  코어: {getattr(quotas, 'cores', 'N/A')}")
            print(f"  RAM: {getattr(quotas, 'ram', 'N/A')} MB")
            
        except Exception as e:
            print(f"❌ 쿼터 조회 실패: {e}")
        
        print()
        
        # 5. 사용량 조회 (또 다른 방법)
        print("--- 프로젝트 사용량 조회 ---")
        try:
            project_id = conn.current_project_id
            usage = conn.compute.get_usage(project_id)
            
            print(f"✅ 사용량 조회 성공:")
            print(f"  총 인스턴스 시간: {getattr(usage, 'total_instance_usage', 'N/A')}")
            print(f"  총 vCPU 시간: {getattr(usage, 'total_vcpus_usage', 'N/A')}")
            print(f"  총 메모리 시간: {getattr(usage, 'total_memory_mb_usage', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 사용량 조회 실패: {e}")
            
    except Exception as e:
        print(f"❌ OpenStack 연결 실패: {e}")

if __name__ == "__main__":
    diagnose_openstack_access()
