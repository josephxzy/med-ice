#!/usr/bin/env bash
# med-ice Linux 一键安装脚本
# 构建词库、部署到系统 Rime 目录、重新部署生效
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${SCRIPT_DIR}/tool/build/out"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# ----- 检测 Rime 用户目录 -----
detect_rime_dir() {
  if [[ -n "${RIME_USER_DIR:-}" ]]; then
    echo "${RIME_USER_DIR}"
    return
  fi

  # fcitx5-rime
  if [[ -d "${HOME}/.local/share/fcitx5/rime" ]]; then
    echo "${HOME}/.local/share/fcitx5/rime"
    return
  fi

  # ibus-rime
  if [[ -d "${HOME}/.config/ibus/rime" ]]; then
    echo "${HOME}/.config/ibus/rime"
    return
  fi

  # fcitx-rime
  if [[ -d "${HOME}/.config/fcitx/rime" ]]; then
    echo "${HOME}/.config/fcitx/rime"
    return
  fi

  echo ""
}

RIME_DIR="$(detect_rime_dir)"

# ----- 参数处理 -----
DO_BUILD=true
DO_DEPLOY=true
DO_BACKUP=false

usage() {
  echo "用法: $0 [选项]"
  echo ""
  echo "选项:"
  echo "  --build-only     仅构建，不部署到系统"
  echo "  --deploy-only    仅部署（跳过构建，需先构建过）"
  echo "  --rime-dir DIR   指定 Rime 用户目录"
  echo "  --backup         部署前备份现有配置"
  echo "  -h, --help       显示帮助"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-only) DO_DEPLOY=false ;;
    --deploy-only) DO_BUILD=false ;;
    --rime-dir) RIME_DIR="$2"; shift ;;
    --backup) DO_BACKUP=true ;;
    -h|--help) usage ;;
    *) echo "未知选项: $1"; usage ;;
  esac
  shift
done

# ----- 构建 -----
if ${DO_BUILD}; then
  echo -e "${GREEN}[1/3] 构建词库...${NC}"
  make -C "${SCRIPT_DIR}/tool/build" build
  echo ""
fi

# ----- 部署 -----
if ${DO_DEPLOY}; then
  if [[ -z "${RIME_DIR}" ]]; then
    echo -e "${RED}未检测到 Rime 用户目录。${NC}"
    echo ""
    echo "请手动指定:"
    echo "  $0 --rime-dir ~/.local/share/fcitx5/rime"
    echo ""
    echo "常见路径:"
    echo "  fcitx5: ~/.local/share/fcitx5/rime"
    echo "  ibus:   ~/.config/ibus/rime"
    echo "  fcitx:  ~/.config/fcitx/rime"
    exit 1
  fi

  echo -e "${GREEN}[2/3] 部署到 ${RIME_DIR}${NC}"

  if ${DO_BACKUP} && [[ -f "${RIME_DIR}/default.yaml" ]]; then
    BACKUP="${RIME_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  备份现有配置到 ${BACKUP}"
    cp -r "${RIME_DIR}" "${BACKUP}"
  fi

  mkdir -p "${RIME_DIR}"

  # 复制构建产物（不覆盖用户已有的 installation.yaml）
  for item in "${OUT_DIR}"/*; do
    name="$(basename "${item}")"
    if [[ "${name}" == "installation.yaml" ]] && [[ -f "${RIME_DIR}/installation.yaml" ]]; then
      echo "  跳过 installation.yaml（保留现有）"
      continue
    fi
    if [[ -d "${item}" ]]; then
      cp -r "${item}" "${RIME_DIR}/"
    else
      cp "${item}" "${RIME_DIR}/"
    fi
  done
  echo ""

  # ----- 部署 -----
  echo -e "${GREEN}[3/3] 部署 Rime...${NC}"
  if command -v rime_deployer &>/dev/null; then
    rime_deployer --build "${RIME_DIR}" "${RIME_DIR}"
    echo ""
    echo -e "${GREEN}完成！${NC}"
    echo "请重新启动输入法（fcitx5 -r 或 ibus restart）使其生效。"
  else
    echo -e "${RED}未找到 rime_deployer，请手动部署：${NC}"
    echo "  sudo apt install librime-bin"
    echo "  rime_deployer --build ${RIME_DIR} ${RIME_DIR}"
  fi
fi
