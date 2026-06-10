"""
Witty Service 统一配置管理

所有环境变量集中在此模块管理，支持的配置项详见下方各配置类。

环境变量列表:
    # 基础配置
    AUTH_TOKEN                      认证令牌 (默认: dev-token)

    # 工作空间配置
    WITTY_WORKSPACE_ROOT           工作空间根目录 (默认: ~/.witty)
    WITTY_AGENT_SERVER_APP_DIR     Agent服务器应用目录 (可选)

    # 数据库配置
    WITTY_DATABASE_URL             数据库连接URL (默认: sqlite:///~/.witty/db/witty_service.sqlite3)

    # 日志配置
    WITTY_LOG_LEVEL                日志级别: DEBUG, INFO, WARNING, ERROR (默认: INFO)
    WITTY_LOG_FILE                 日志文件路径 (默认: WITTY_WORKSPACE_ROOT/logs/witty-service.log)
    WITTY_LOG_MAX_BYTES            单个日志文件最大字节数 (默认: 10485760)
    WITTY_LOG_BACKUP_COUNT         备份日志文件数量 (默认: 5)

    # Docker沙箱配置
    WITTY_DOCKER_HOST              Docker主机地址 (默认: 127.0.0.1)
    WITTY_DOCKER_CONTAINER_PORT    Docker容器端口 (默认: 8080)
    WITTY_DOCKER_CONTAINER_WORKSPACE_PATH  Docker容器内工作空间路径 (默认: /witty-workspace)
    WITTY_DOCKER_STOP_TIMEOUT      Docker容器停止超时时间(秒) (默认: 10)
    WITTY_DOCKER_IMAGE             Docker镜像名称 (默认: witty-agent-server)
    WITTY_DOCKER_IMAGE_TAG         Docker镜像标签 (默认: latest)

    # OpenClaw Gateway配置
    OPENCLAW_GATEWAY_IDLE_TIMEOUT            网关空闲超时时间(秒) (默认: 1200)
    OPENCLAW_GATEWAY_LIFECYCLE_END_DRAIN_TIMEOUT  生命周期结束排水超时时间(秒) (默认: 60)
    OPENCLAW_STATE_DIR               状态目录 (可选)

    # OpenClaw配置
    OPENCLAW_CONFIG_PATH            OpenClaw配置文件路径 (默认: ~/.openclaw/openclaw.json)

使用示例:
    from witty_service.config import get_settings

    settings = get_settings()
    print(settings.database.url)
    print(settings.docker.host)
    print(settings.logging.level)
"""

from dataclasses import dataclass, field
from pathlib import Path
import os


# ==============================================================================
# CORS 配置
# ==============================================================================

@dataclass(frozen=True)
class CorsSettings:
    """CORS 跨域资源共享配置"""
    origins: list[str] = field(default_factory=lambda: ["*"])
    credentials: bool = True
    methods: list[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    headers: list[str] = field(default_factory=lambda: ["*"])


# ==============================================================================
# 数据库配置
# ==============================================================================

@dataclass(frozen=True)
class DatabaseSettings:
    """数据库连接配置
    
    环境变量:
        WITTY_DATABASE_URL: 数据库连接URL
            - SQLite: sqlite:///path/to/db.sqlite3
            - PostgreSQL: postgresql://user:pass@localhost/dbname
            - 默认: sqlite:///~/.witty/db/witty_service.sqlite3
    """
    url: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        default_db_path = Path("~/.witty/db/witty_service.sqlite3").expanduser()
        url = os.getenv("WITTY_DATABASE_URL", f"sqlite:///{default_db_path}")
        return cls(url=url)


# ==============================================================================
# 日志配置
# ==============================================================================

@dataclass(frozen=True)
class LoggingSettings:
    """日志系统配置
    
    环境变量:
        WITTY_LOG_LEVEL: 日志级别 (DEBUG, INFO, WARNING, ERROR), 默认 INFO
        WITTY_LOG_FILE: 日志文件路径, 默认 WITTY_WORKSPACE_ROOT/logs/witty-service.log
        WITTY_LOG_MAX_BYTES: 单个日志文件最大字节数, 默认 10MB
        WITTY_LOG_BACKUP_COUNT: 备份日志文件数量, 默认 5
    """
    level: str = "INFO"
    file: str = ""
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5

    @classmethod
    def from_env(cls) -> "LoggingSettings":
        workspace_root = Path(os.getenv("WITTY_WORKSPACE_ROOT", "~/.witty")).expanduser()
        default_log_file = workspace_root / "logs" / "witty-service.log"
        return cls(
            level=os.getenv("WITTY_LOG_LEVEL", "INFO").upper(),
            file=os.getenv("WITTY_LOG_FILE", str(default_log_file)),
            max_bytes=int(os.getenv("WITTY_LOG_MAX_BYTES", 10 * 1024 * 1024)),
            backup_count=int(os.getenv("WITTY_LOG_BACKUP_COUNT", 5)),
        )


# ==============================================================================
# Docker 沙箱配置
# ==============================================================================

@dataclass(frozen=True)
class DockerSettings:
    """Docker 沙箱运行时配置
    
    环境变量:
        WITTY_DOCKER_HOST: Docker 守护进程主机地址, 默认 127.0.0.1
        WITTY_DOCKER_CONTAINER_PORT: 容器内部服务端口, 默认 8080
        WITTY_DOCKER_CONTAINER_WORKSPACE_PATH: 容器内工作空间挂载路径, 默认 /witty-workspace
        WITTY_DOCKER_STOP_TIMEOUT: 容器停止超时时间(秒), 默认 10
        WITTY_DOCKER_IMAGE: Docker 镜像名称, 默认 witty-agent-server
        WITTY_DOCKER_IMAGE_TAG: Docker 镜像标签, 默认 latest
    """
    host: str = "127.0.0.1"
    container_port: int = 8080
    container_workspace_path: str = "/witty-workspace"
    stop_timeout: int = 10
    image: str = "witty-agent-server"
    image_tag: str = "latest"

    @classmethod
    def from_env(cls) -> "DockerSettings":
        return cls(
            host=os.getenv("WITTY_DOCKER_HOST", "127.0.0.1"),
            container_port=int(os.getenv("WITTY_DOCKER_CONTAINER_PORT", 8080)),
            container_workspace_path=os.getenv("WITTY_DOCKER_CONTAINER_WORKSPACE_PATH", "/witty-workspace"),
            stop_timeout=int(os.getenv("WITTY_DOCKER_STOP_TIMEOUT", 10)),
            image=os.getenv("WITTY_DOCKER_IMAGE", "witty-agent-server"),
            image_tag=os.getenv("WITTY_DOCKER_IMAGE_TAG", "latest"),
        )

    def get_full_image_name(self) -> str:
        """获取完整的镜像名称，包含标签"""
        image = self.image
        if "@" in image or self._has_explicit_tag(image):
            return image
        return f"{image}:{self.image_tag}"

    @staticmethod
    def _has_explicit_tag(image: str) -> bool:
        """检查镜像名是否包含显式标签"""
        last_segment = image.rsplit("/", 1)[-1]
        return ":" in last_segment


# ==============================================================================
# OpenClaw Gateway 配置
# ==============================================================================

@dataclass(frozen=True)
class OpenClawGatewaySettings:
    """OpenClaw Gateway 网关配置
    
    环境变量:
        OPENCLAW_GATEWAY_IDLE_TIMEOUT: 网关空闲超时时间(秒), 默认 1200 (20分钟)
        OPENCLAW_GATEWAY_LIFECYCLE_END_DRAIN_TIMEOUT: 生命周期结束排水超时时间(秒), 默认 60
        OPENCLAW_STATE_DIR: 网关状态存储目录, 默认 ~/.openclaw
    """
    idle_timeout: float = 1200.0
    lifecycle_end_drain_timeout: float = 60.0
    state_dir: str | None = None

    @classmethod
    def from_env(cls) -> "OpenClawGatewaySettings":
        return cls(
            idle_timeout=float(os.getenv("OPENCLAW_GATEWAY_IDLE_TIMEOUT", "1200")),
            lifecycle_end_drain_timeout=float(os.getenv("OPENCLAW_GATEWAY_LIFECYCLE_END_DRAIN_TIMEOUT", "60")),
            state_dir=os.getenv("OPENCLAW_STATE_DIR"),
        )


# ==============================================================================
# 工作空间配置
# ==============================================================================

@dataclass(frozen=True)
class WorkspaceSettings:
    """工作空间目录配置
    
    环境变量:
        WITTY_WORKSPACE_ROOT: 工作空间根目录, 默认 ~/.witty
        WITTY_AGENT_SERVER_APP_DIR: Agent 服务器应用目录, 可选
        WITTY_RECOVERY_MAX_CONCURRENT: 启动时恢复 agent 的最大并发数, 默认 5
    """
    root: str = "~/.witty"
    agent_server_app_dir: str | None = None
    recovery_max_concurrent: int = 5

    @classmethod
    def from_env(cls) -> "WorkspaceSettings":
        return cls(
            root=os.getenv("WITTY_WORKSPACE_ROOT", "~/.witty"),
            agent_server_app_dir=os.getenv("WITTY_AGENT_SERVER_APP_DIR"),
            recovery_max_concurrent=int(os.getenv("WITTY_RECOVERY_MAX_CONCURRENT", "5")),
        )

    def root_path(self) -> Path:
        """获取工作空间根目录 (Path 对象)"""
        return Path(self.root).expanduser()


# ==============================================================================
# OpenClaw 配置
# ==============================================================================

@dataclass(frozen=True)
class OpenClawSettings:
    """OpenClaw 通用配置
    
    环境变量:
        OPENCLAW_CONFIG_PATH: OpenClaw 配置文件路径, 默认 ~/.openclaw/openclaw.json
    """
    config_path: str = "~/.openclaw/openclaw.json"

    @classmethod
    def from_env(cls) -> "OpenClawSettings":
        return cls(
            config_path=os.getenv("OPENCLAW_CONFIG_PATH", "~/.openclaw/openclaw.json"),
        )

    def config_path_resolved(self) -> Path:
        """获取配置文件路径 (Path 对象)"""
        return Path(self.config_path).expanduser().resolve(strict=False)


# ==============================================================================
# 主配置类
# ==============================================================================

@dataclass(frozen=True)
class Settings:
    """Witty Service 统一配置容器
    
    整合所有子配置模块，通过 from_env() 类方法从环境变量加载配置。
    使用 get_settings() 函数获取单例配置实例。
    """
    auth_token: str
    cors: CorsSettings
    database: DatabaseSettings
    logging: LoggingSettings
    docker: DockerSettings
    openclaw_gateway: OpenClawGatewaySettings
    workspace: WorkspaceSettings
    openclaw: OpenClawSettings

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载所有配置"""
        return cls(
            auth_token=os.getenv("AUTH_TOKEN", "dev-token"),
            cors=CorsSettings(),
            database=DatabaseSettings.from_env(),
            logging=LoggingSettings.from_env(),
            docker=DockerSettings.from_env(),
            openclaw_gateway=OpenClawGatewaySettings.from_env(),
            workspace=WorkspaceSettings.from_env(),
            openclaw=OpenClawSettings.from_env(),
        )


# ==============================================================================
# 配置访问接口
# ==============================================================================

_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置单例实例
    
    使用全局单例模式，首次调用时从环境变量加载配置，
    后续调用直接返回缓存的配置实例。
    
    Returns:
        Settings: 配置实例
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def get_docker_image() -> str:
    """获取 Docker 镜像完整名称
    
    Returns:
        str: 完整的镜像名称，包含标签
    """
    return get_settings().docker.get_full_image_name()
