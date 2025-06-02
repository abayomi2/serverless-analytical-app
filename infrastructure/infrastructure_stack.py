from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
)
from aws_cdk.aws_ecr_assets import Platform
from constructs import Construct
import os

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Define a VPC (Virtual Private Cloud)
        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=2,
            nat_gateways=1
        )

        # 2. Create an ECS Cluster
        cluster = ecs.Cluster(self, "MyCluster",
            vpc=vpc
        )

        # 3. Define the Fargate Service with Application Load Balancer
        project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "MyFargateService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    directory=project_root_path,
                    platform=Platform.LINUX_AMD64  # ✅ Ensure compatibility with Fargate
                ),
                container_port=8000,
                environment={
                    "EXAMPLE_VARIABLE": "example_value"
                }
            ),
            public_load_balancer=True,
        )

        # 4. Configure Health Check
        fargate_service.target_group.configure_health_check(
            path="/",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=2,
            healthy_http_codes="200-299"
        )

        # 5. Output the DNS name
        CfnOutput(self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="The DNS name of the Application Load Balancer"
        )
