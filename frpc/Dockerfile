# 使用轻量级的 Alpine Linux 作为基础镜像
FROM alpine:latest

# 安装必要的依赖
RUN apk add --no-cache ca-certificates tzdata

# 设置时区
ENV TZ=Asia/Shanghai

# 创建必要的目录
RUN mkdir -p /etc/frp /var/log

# 复制 frpc 二进制文件到容器中
COPY frpc /usr/local/bin/frpc

# 设置执行权限
RUN chmod +x /usr/local/bin/frpc

# 创建非 root 用户
RUN addgroup -g 1000 frpc && \
    adduser -D -s /bin/sh -u 1000 -G frpc frpc

# 切换到非 root 用户
USER frpc

# 设置工作目录
WORKDIR /home/frpc

# 暴露管理端口（如果需要的话）
EXPOSE 7400

# 启动命令
CMD ["/usr/local/bin/frpc", "-c", "/etc/frp/frpc.toml"]
