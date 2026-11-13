# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ LAYOUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT			= \033[0m
GREEN			= \033[1;32m
CYAN			= \033[1;36m

define ANIMATION
				@for frame in ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏; do \
				printf "$$frame $(1)...\r"; \
				sleep 0.02; \
				done; \
				printf "\n"
endef


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ VARIABLES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAP ?= maps/easy/01_linear_path.txt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install:
				$(call ANIMATION,Installing project dependencies)
				@python3 -m pip install flake8 mypy

run:
				@python3 src/main.py $(MAP)

debug:
				@python3 -m pdb src/main.py $(MAP)

clean:
				$(call ANIMATION,Removing compiled files and caches)
				@rm -rf __pycache__ */__pycache__ .mypy_cache

lint:
				@flake8 .
				@mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
				@flake8 .
				@mypy . --strict

help:
				@printf "Usage: make [target]\n"
				@printf "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
				@printf "$(CYAN)install$(DEFAULT)		- Install project dependencies\n"
				@printf "$(CYAN)run$(DEFAULT)		- Run the main script with map (use MAP=\"<map>\" to pass map)\n"
				@printf "$(CYAN)debug$(DEFAULT)		- Run the main script in debug mode with map (use MAP=\"<map>\" to pass map)\n"
				@printf "$(CYAN)clean$(DEFAULT)		- Remove compiled Python files and caches\n"
				@printf "$(CYAN)lint$(DEFAULT)		- Run linter and type checker to ensure code quality\n"
				@printf "$(CYAN)lint-strict$(DEFAULT)	- Run linter and type checker with strict settings\n"
				@printf "$(CYAN)help$(DEFAULT)		- Show this help message\n"

.PHONY:			install run debug clean lint lint-strict help
