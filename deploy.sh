#!/bin/bash

# 线上部署脚本 

# 拉取最新代码
git pull

# 设置代理
export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890

# 构建并启动服务
docker-compose up -d --build