{
  description = "the-den journal CLI (today) - Python flake via pyproject-nix + uv2nix";

  # Same Python-dev setup as the scufris project (pyproject-nix + uv2nix).
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    flake-parts.url = "github:hercules-ci/flake-parts";

    dashboardd = {
      url = "github:alexjercan/dashboardd/e68a4acdd73b5be73883f4fa435db26a2f16cbab";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    macros = {
      url = "github:alexjercan/macros.nvim/v0.2.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs @ {
    self,
    flake-parts,
    nixpkgs,
    pyproject-nix,
    uv2nix,
    pyproject-build-systems,
    ...
  }: let
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};
    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };
    editableOverlay = workspace.mkEditablePyprojectOverlay {
      root = "$REPO_ROOT";
    };
  in
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin"];
      perSystem = {
        self',
        pkgs,
        system,
        ...
      }: let
        python = pkgs.python3;
        pythonBase = pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        };
        pythonSet = pythonBase.overrideScope (
          nixpkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
          ]
        );
        editablePythonSet = pythonSet.overrideScope editableOverlay;
        virtualenv = editablePythonSet.mkVirtualEnv "today-dev-env" workspace.deps.all;
        inherit (pkgs.callPackages pyproject-nix.build.util {}) mkApplication;

        runtimeVenv = pythonSet.mkVirtualEnv "today-env" workspace.deps.default;
        todayApp = mkApplication {
          venv = runtimeVenv;
          package = pythonSet.today;
        };

        dashboarddWidgetTool = inputs.dashboardd.packages.${system}.dashboardd-widget;
        dashboarddPackage = inputs.dashboardd.packages.${system}.dashboardd;
        macrosPackage = inputs.macros.packages.${system}.default;
        frontendNodeModules = pkgs.importNpmLock.buildNodeModules {
          npmRoot = ./widget/frontend;
          nodejs = pkgs.nodejs_22;
        };
        widgetFrontend = pkgs.stdenvNoCC.mkDerivation {
          pname = "today-widget-frontend";
          version = "0.1.0";
          src = ./widget/frontend;
          nativeBuildInputs = [pkgs.nodejs_22];
          buildPhase = ''
            runHook preBuild
            cp -R ${frontendNodeModules}/node_modules .
            npm run build
            runHook postBuild
          '';
          installPhase = ''
            runHook preInstall
            mkdir -p "$out"
            cp -R dist/. "$out/"
            runHook postInstall
          '';
        };
        widgetBackend = pkgs.writeShellScript "today-dashboardd-widget" ''
          export MACROS_EXECUTABLE=${macrosPackage}/bin/macros
          exec ${todayApp}/bin/today-dashboardd-widget "$@"
        '';
        todayWidget = pkgs.runCommand "today-dashboardd-widget-0.1.0" {
          nativeBuildInputs = [dashboarddWidgetTool];
          meta.description = "Writable Today widgets for dashboardd";
        } ''
          cp -R ${./widget} source
          chmod -R u+w source
          mkdir -p source/dist/bin source/frontend/dist
          cp ${widgetBackend} source/dist/bin/today-dashboardd-widget
          cp -R ${widgetFrontend}/. source/frontend/dist/
          mkdir -p "$out/share/dashboardd/widgets"
          dashboardd-widget pack source/widget.toml \
            --output "$out/share/dashboardd/widgets/today"
          dashboardd-widget check "$out/share/dashboardd/widgets/today"
        '';

        # A check derivation: run one command against a writable source copy.
        mkCheck = name: command:
          pkgs.runCommand "today-${name}" {
            nativeBuildInputs = [virtualenv];
            src = ./.;
          } ''
            cp -r $src work
            chmod -R +w work
            cd work
            export HOME=$TMPDIR
            export PYTHONPATH=
            # The dev venv is an editable install whose .pth resolves the
            # `today` package via $REPO_ROOT (set only in the devShell). Point
            # it at the copied source so `import today` works in the sandbox.
            export REPO_ROOT=$PWD
            ${command}
            touch $out
          '';
      in {
        packages = {
          today = todayApp.overrideAttrs (old: {
            meta = (old.meta or {}) // {mainProgram = "today";};
          });
          dashboardd-widget = todayWidget;
          default = todayApp.overrideAttrs (old: {
            meta = (old.meta or {}) // {mainProgram = "today";};
          });
        };

        apps = {
          today = {
            type = "app";
            program = "${self.packages.${system}.today}/bin/today";
            meta.description = "the-den journal CLI";
          };
          default = self'.apps.today;
        };

        checks = {
          ruff = mkCheck "ruff" "ruff check .";
          mypy = mkCheck "mypy" "mypy .";
          pytest = mkCheck "pytest" "pytest";
          widget-frontend = widgetFrontend;
          widget-package = pkgs.runCommand "today-widget-package-check" {
            nativeBuildInputs = [dashboarddWidgetTool pkgs.jq];
          } ''
            bundle=${todayWidget}/share/dashboardd/widgets/today
            dashboardd-widget check "$bundle"
            test "$(jq '.variants | length' "$bundle/widget.json")" -eq 6
            test -x "$bundle/bin/today"
            grep -q ${macrosPackage}/bin/macros "$bundle/bin/today"
            touch "$out"
          '';
          widget-catalog = pkgs.runCommand "today-widget-catalog-check" {
            nativeBuildInputs = [dashboarddPackage pkgs.curl pkgs.jq];
          } ''
            export DASHBOARDD_WIDGET_PATH="${dashboarddPackage}/share/dashboardd/widgets:${todayWidget}/share/dashboardd/widgets"
            export DASHBOARDD_PORT=17322
            export DASHBOARDD_STATE_FILE="$TMPDIR/dashboard.json"
            export DASHBOARDD_CONFIG_FILE="$TMPDIR/config.toml"
            dashboardd >dashboardd.log 2>&1 &
            pid=$!
            trap 'kill "$pid" 2>/dev/null || true' EXIT
            ready=0
            for _ in $(seq 1 50); do
              if curl --fail --silent http://127.0.0.1:17322/health >/dev/null; then
                ready=1
                break
              fi
              sleep 0.1
            done
            if [ "$ready" -ne 1 ]; then
              cat dashboardd.log
              exit 1
            fi
            curl --fail --silent http://127.0.0.1:17322/api/v1/widgets >catalog.json
            test "$(jq '[.widgets[] | select(.id == "today")][0].variants | length' catalog.json)" -eq 6
            kill -INT "$pid"
            wait "$pid"
            trap - EXIT
            touch "$out"
          '';
        };

        devShells.default = pkgs.mkShell {
          packages = [virtualenv pkgs.uv];
          env = {
            UV_NO_SYNC = "1";
            UV_PYTHON = editablePythonSet.python.interpreter;
            UV_PYTHON_DOWNLOADS = "never";
          };
          shellHook = ''
            unset PYTHONPATH
            export REPO_ROOT=$(git rev-parse --show-toplevel)
            source ${virtualenv}/bin/activate
          '';
        };
      };

      # System-agnostic overlay so nix.dotfiles (and any consumer) can add
      # `today` to its package set via `inputs.today.overlays.default` (the
      # tatr pattern), then `home.packages = [pkgs.today]`.
      flake = {
        overlays.default = final: _prev: {
          today = self.packages.${final.stdenv.hostPlatform.system}.today;
        };

        skills.today = builtins.path {
          path = ./skills/today;
          name = "today-skill";
        };
      };
    };
}
