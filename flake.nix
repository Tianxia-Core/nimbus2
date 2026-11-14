# ffp: FFP-NIMBUS2-FLAKE declarative nix
{
  description = "Nimbus² v2.5.0 — Tier-2 Polyglot Proxy, Route Benchmark & Post-Quantum Mesh Transit Enclave";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    tianxia-core = {
      url = "github:Tianxia-Core/TianxiaOS";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, tianxia-core, ... }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in {
      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [ rustc cargo go python3 ];
          };
        }
      );
    };
}
