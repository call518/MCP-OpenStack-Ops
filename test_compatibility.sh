#!/bin/bash
# SDK 버전별 호환성 테스트 스크립트

echo "=== OpenStack SDK 호환성 테스트 ==="

# 각 릴리즈별 이미지로 기본 기능 테스트
RELEASES=("yoga" "zed" "antelope" "bobcat" "caracal" "dalmatian" "epoxy" "flamingo")

for release in "${RELEASES[@]}"; do
    echo
    echo "--- Testing $release release ---"
    
    # 해당 릴리즈 이미지로 간단한 연결 테스트
    docker run --rm \
        --env-file .env \
        "call518/mcp-server-openstack-ops:${release}" \
        python -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from mcp_openstack_ops.functions import get_openstack_connection
    conn = get_openstack_connection()
    print(f'✅ {release}: Connection successful')
    
    # 기본 API 테스트
    list(conn.compute.servers(limit=1))
    print(f'✅ {release}: Compute API working')
    
except Exception as e:
    print(f'❌ {release}: Error - {e}')
" || echo "❌ $release: Failed to start container"
    
done

echo
echo "=== 호환성 테스트 완료 ==="
