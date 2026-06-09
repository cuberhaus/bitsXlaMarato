# ─── Cross-platform support ────────────────────────────────────────
# On Windows, use Git Bash's sh.exe so POSIX utilities (grep, awk,
# git, npx …) are available in recipe lines.
ifeq ($(OS),Windows_NT)
  SHELL := C:/Program Files/Git/bin/sh.exe
  .SHELLFLAGS := -c
endif

.PHONY: help skills-list skills-update skills-restore

default: help

##@ Skills

skills-list: ## List project skills installed via skills-lock.json
	@npx skills list -p

skills-update: ## Update project skills and show what changed
	@npx skills update -p -y
	@echo ""
	@echo "Changed skill files:"
	@git diff --name-only -- .agents/skills skills-lock.json || true

skills-restore: ## Restore pinned skills from skills-lock.json
	@npx skills experimental_install

##@ General

help: ## Show this help message
	@awk ' \
		/^##@/      { printf "\n\033[1m%s\033[0m\n", substr($$0, 5); next } \
		/^[a-zA-Z_-]+:.*##/ { \
			split($$0, parts, ":.*## *"); \
			printf "  \033[36m%-20s\033[0m %s\n", parts[1], parts[2] \
		} \
	' $(MAKEFILE_LIST) || true
