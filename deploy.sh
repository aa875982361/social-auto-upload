#!/bin/bash

# 线上部署脚本 

# 拉取最新代码
git pull

# 构建并启动服务
docker-compose up -d --build