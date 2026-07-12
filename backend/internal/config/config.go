package config

import (
	"os"

	"github.com/spf13/viper"
)

// Config 应用配置
type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	MinIO    MinIOConfig
	NATS     NATSConfig
	AI       AIConfig
	Feishu   FeishuConfig
	JWT      JWTConfig
}

type ServerConfig struct {
	Port string
	Mode string
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Name     string
	SSLMode  string
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

type MinIOConfig struct {
	Endpoint  string
	AccessKey string
	SecretKey string
	Bucket    string
	UseSSL    bool
}

type NATSConfig struct {
	URL string
}

type AIConfig struct {
	APIKey   string
	Provider string
}

type FeishuConfig struct {
	AppID     string
	AppSecret string
}

type JWTConfig struct {
	Secret string
	Expire int // 小时
}

// Load 加载配置
func Load() *Config {
	viper.SetDefault("server.port", "8080")
	viper.SetDefault("server.mode", "release")
	viper.SetDefault("database.host", "localhost")
	viper.SetDefault("database.port", "5432")
	viper.SetDefault("database.user", "opportunity")
	viper.SetDefault("database.password", "opportunity123")
	viper.SetDefault("database.name", "opportunity_system")
	viper.SetDefault("database.sslmode", "disable")
	viper.SetDefault("redis.host", "localhost")
	viper.SetDefault("redis.port", "6379")
	viper.SetDefault("redis.db", 0)
	viper.SetDefault("minio.endpoint", "localhost:9000")
	viper.SetDefault("minio.bucket", "opportunity")
	viper.SetDefault("nats.url", "nats://localhost:4222")
	viper.SetDefault("ai.provider", "qianwen")
	viper.SetDefault("jwt.secret", "your-jwt-secret-change-in-production")
	viper.SetDefault("jwt.expire", 24)

	// 显式绑定环境变量
	bindEnv("server.port", "SERVER_PORT")
	bindEnv("server.mode", "GIN_MODE")
	bindEnv("database.host", "DB_HOST")
	bindEnv("database.port", "DB_PORT")
	bindEnv("database.user", "DB_USER")
	bindEnv("database.password", "DB_PASSWORD")
	bindEnv("database.name", "DB_NAME")
	bindEnv("database.sslmode", "DB_SSLMODE")
	bindEnv("redis.host", "REDIS_HOST")
	bindEnv("redis.port", "REDIS_PORT")
	bindEnv("redis.password", "REDIS_PASSWORD")
	bindEnv("redis.db", "REDIS_DB")
	bindEnv("minio.endpoint", "MINIO_ENDPOINT")
	bindEnv("minio.access_key", "MINIO_ACCESS_KEY")
	bindEnv("minio.secret_key", "MINIO_SECRET_KEY")
	bindEnv("minio.bucket", "MINIO_BUCKET")
	bindEnv("minio.use_ssl", "MINIO_USE_SSL")
	bindEnv("nats.url", "NATS_URL")
	bindEnv("ai.api_key", "AI_API_KEY")
	bindEnv("ai.provider", "AI_PROVIDER")
	bindEnv("feishu.app_id", "FEISHU_APP_ID")
	bindEnv("feishu.app_secret", "FEISHU_APP_SECRET")
	bindEnv("jwt.secret", "JWT_SECRET")
	bindEnv("jwt.expire", "JWT_EXPIRE")

	return &Config{
		Server: ServerConfig{
			Port: viper.GetString("server.port"),
			Mode: viper.GetString("server.mode"),
		},
		Database: DatabaseConfig{
			Host:     viper.GetString("database.host"),
			Port:     viper.GetString("database.port"),
			User:     viper.GetString("database.user"),
			Password: viper.GetString("database.password"),
			Name:     viper.GetString("database.name"),
			SSLMode:  viper.GetString("database.sslmode"),
		},
		Redis: RedisConfig{
			Host:     viper.GetString("redis.host"),
			Port:     viper.GetString("redis.port"),
			Password: viper.GetString("redis.password"),
			DB:       viper.GetInt("redis.db"),
		},
		MinIO: MinIOConfig{
			Endpoint:  viper.GetString("minio.endpoint"),
			AccessKey: viper.GetString("minio.access_key"),
			SecretKey: viper.GetString("minio.secret_key"),
			Bucket:    viper.GetString("minio.bucket"),
			UseSSL:    viper.GetBool("minio.use_ssl"),
		},
		NATS: NATSConfig{
			URL: viper.GetString("nats.url"),
		},
		AI: AIConfig{
			APIKey:   viper.GetString("ai.api_key"),
			Provider: viper.GetString("ai.provider"),
		},
		Feishu: FeishuConfig{
			AppID:     viper.GetString("feishu.app_id"),
			AppSecret: viper.GetString("feishu.app_secret"),
		},
		JWT: JWTConfig{
			Secret: viper.GetString("jwt.secret"),
			Expire: viper.GetInt("jwt.expire"),
		},
	}
}

func bindEnv(key, envVar string) {
	if val := os.Getenv(envVar); val != "" {
		viper.Set(key, val)
	}
}
