#!/usr/bin/env python3
"""
MASTER EXECUTION ORCHESTRATOR
Project: Magnetohydrodynamic Hybrid Nanofluid Cooling of Lithium-Ion Batteries:
         A Coupled Porous Medium and Data-Driven Modeling Approach

Provides an interactive CLI menu and argument-driven execution for all 4 subparts:
  - Subpart A1: Individual Formula Numerical Calculator (All 18 Formulations)
  - Subpart A2: Coupled 2D BTMS Numerical Solver (Darcy-Brinkman MHD + Energy)
  - Subpart B1 (Data): Physics-Informed Dataset Generation
  - Subpart B1 (Train): Machine Learning Training & Benchmark (5 Models)
  - Subpart B2: ML-Based Prediction, Comparison, and Visualization
  - Complete Suite: Runs A1 -> A2 -> B1 (Data) -> B1 (Train) -> B2
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import sys
import argparse
import subprocess

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    banner = """
========================================================================================
   MAGNETOHYDRODYNAMIC HYBRID NANOFLUID COOLING OF LITHIUM-ION BATTERIES:
   A COUPLED POROUS MEDIUM AND DATA-DRIVEN MODELING APPROACH
========================================================================================
  Academic Research Simulation, Machine Learning & Interactive 3D Digital Twin
  Implementation of All 18 Formulations + Interactive 3D 50-Cell BTMS (24 Equations)
========================================================================================
"""
    print(banner)


def run_subpart_a1():
    from part_a_without_ml.A1_formula_calculator import run_all_18_formulations
    run_all_18_formulations()


def run_subpart_a2():
    from part_a_without_ml.A2_physics_solver import run_subpart_a2
    run_subpart_a2()


def run_subpart_b1_data(samples: int = 1500):
    from part_b_with_ml.B1_dataset_generation import generate_physics_dataset
    generate_physics_dataset(n_samples=samples)


def run_subpart_b1_train():
    from part_b_with_ml.B1_model_training import train_and_evaluate_all_models
    train_and_evaluate_all_models()


def run_subpart_b2():
    from part_b_with_ml.B2_prediction import predict_btms_performance
    predict_btms_performance()


def run_3d_simulation():
    from main_3d import main as run_3d_main
    run_3d_main()


def run_3d_btms():
    print("\n>>> LAUNCHING INTERACTIVE 3D BTMS SIMULATION <<<\n")
    from btms_3d.run_btms_3d import main as run_3d_app
    run_3d_app()


def run_all_subparts():
    print("\n>>> EXECUTING COMPLETE SIMULATION & MACHINE LEARNING PIPELINE <<<\n")
    print("\n--- STEP 1: SUBPART A1 (18 FORMULAS CALCULATOR) ---")
    run_subpart_a1()

    print("\n--- STEP 2: SUBPART A2 (2D COUPLED PHYSICS SOLVER) ---")
    run_subpart_a2()

    print("\n--- STEP 3: SUBPART B1 (DATASET GENERATION) ---")
    run_subpart_b1_data(samples=1500)

    print("\n--- STEP 4: SUBPART B1 (MODEL TRAINING) ---")
    run_subpart_b1_train()

    print("\n--- STEP 5: SUBPART B2 (PREDICTION & VERIFICATION) ---")
    run_subpart_b2()

    print("\n" + "=" * 90)
    print(" ALL SUBPARTS COMPLETED SUCCESSFULLY ".center(90, "="))
    print("=" * 90)


def run_unit_tests():
    print("\n>>> EXECUTING COMPREHENSIVE SCIENTIFIC TEST SUITE <<<\n")
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


def interactive_menu():
    print_banner()
    while True:
        print("\nMAIN EXECUTION MENU:")
        print("  [1] Subpart A1: Individual Formula Numerical Calculator (Formulas 1 - 18)")
        print("  [2] Subpart A2: Coupled 2D BTMS Numerical Physics Solver (Darcy-Brinkman MHD)")
        print("  [3] Subpart B1 (Part 1): Generate Physics-Informed Synthetic Dataset")
        print("  [4] Subpart B1 (Part 2): Train & Benchmark 5 ML Models (RF, XGB, SVR, GB, MLP)")
        print("  [5] Subpart B2: ML Prediction, Comparison, and Visualization")
        print("  [6] Execute Full Pipeline (A1 -> A2 -> B1 Data -> B1 Train -> B2)")
        print("  [7] Run Automated Scientific Validation Tests")
        print("  [8] Launch Interactive 3D BTMS Simulation (WebGL / Three.js)")
        print("  [0] Exit")

        choice = input("\nEnter your choice [0-8]: ").strip()
        if choice == "1":
            run_subpart_a1()
        elif choice == "2":
            run_subpart_a2()
        elif choice == "3":
            s_str = input("Enter number of samples [default: 1500]: ").strip()
            s = int(s_str) if s_str.isdigit() else 1500
            run_subpart_b1_data(samples=s)
        elif choice == "4":
            run_subpart_b1_train()
        elif choice == "5":
            run_subpart_b2()
        elif choice == "6":
            run_all_subparts()
        elif choice == "7":
            run_unit_tests()
        elif choice == "8":
            run_3d_btms()
        elif choice == "0":
            print("\nExiting BTMS Simulation System. Goodbye!\n")
            break
        else:
            print("Invalid selection. Please choose an option from 0 to 7.")


def main():
    parser = argparse.ArgumentParser(description="BTMS MHD Hybrid Nanofluid Simulation Master Runner")
    parser.add_argument(
        "--subpart",
        type=str,
        choices=["A1", "A2", "B1_data", "B1_train", "B2", "3D", "all", "test"],
        help="Specify which subpart to execute non-interactively"
    )
    parser.add_argument("--samples", type=int, default=1500, help="Dataset sample count for B1_data")
    args = parser.parse_args()

    if args.subpart:
        print_banner()
        if args.subpart == "A1":
            run_subpart_a1()
        elif args.subpart == "A2":
            run_subpart_a2()
        elif args.subpart == "B1_data":
            run_subpart_b1_data(samples=args.samples)
        elif args.subpart == "B1_train":
            run_subpart_b1_train()
        elif args.subpart == "B2":
            run_subpart_b2()
        elif args.subpart == "3D":
            run_3d_btms()
        elif args.subpart == "all":
            run_all_subparts()
        elif args.subpart == "test":
            run_unit_tests()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
