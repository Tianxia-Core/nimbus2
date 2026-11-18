# ffp: FFP-NIX-FLAKE declarative nix
{
  description = "Nimbus2 v2.6.0 — Nimbus2 Sovereign Executive Build Manager, Autonomous PR Reviewer & Polyglot Proxy Suite";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs, ... }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      artifactMeta = {
        "x86_64-linux" = {
          url = "https://github.com/Tianxia-Core/nimbus2/releases/download/v2.6.0/nimbus2-v2.6.0-linux-x86_64";
          sha256 = "350a753e7e6685fc8e2f9189e3e9c161cb1135b5cd3b8ac3127a4a86b4b990fb";
        };
        "aarch64-linux" = {
          url = "https://github.com/Tianxia-Core/nimbus2/releases/download/v2.6.0/nimbus2-v2.6.0-linux-aarch64";
          sha256 = "e81350e2035099383b074f2ca6954006f395dab777c21fcc4ffedb7fc6003fe9";
        };
      };
      mkSovereignPkg = pkgs: system:
        let
          metaInfo = artifactMeta.${system};
        in
        pkgs.stdenvNoCC.mkDerivation {
          pname = "nimbus2";
          version = "2.6.0";
          src = pkgs.fetchurl {
            inherit (metaInfo) url sha256;
          };
          dontUnpack = true;
          installPhase = ''
            runHook preInstall
            mkdir -p $out/bin
            install -m 0755 $src $out/bin/nimbus2
            runHook postInstall
          '';
          meta = with pkgs.lib; {
            description = "Nimbus2 Sovereign Executive Build Manager, Autonomous PR Reviewer & Polyglot Proxy Suite";
            homepage = "https://rasaxmachina.com";
            platforms = supportedSystems;
            mainProgram = "nimbus2";
          };
        };
    in {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pkg = mkSovereignPkg pkgs system;
        in {
          default = pkg;
          "nimbus2" = pkg;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/nimbus2";
        };
      });

      overlays.default = final: prev: {
        "nimbus2" = mkSovereignPkg final final.stdenv.hostPlatform.system;
      };

      nixosModules.nimbus2 = { config, lib, pkgs, ... }:
        let
          cfg = config.services.nimbus2;
        in {
          options.services.nimbus2 = {
            enable = lib.mkEnableOption "Nimbus2 Sovereign Service";
            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
              description = "Package providing nimbus2.";
            };
          };
          config = lib.mkIf cfg.enable {
            environment.systemPackages = [ cfg.package ];
          };
        };
    };
}
