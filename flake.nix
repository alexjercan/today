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
    };
}
