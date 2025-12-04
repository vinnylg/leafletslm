# DrugsLM Documentation

May be the same of README.md
May be the same of README.md

## Description 

Consolidated repository for ETL, modeling, experiments, and deployment of the master's thesis in Computer Science at the Department of Computer Science of the Federal University of Paraná, Curitiba - Brazil, focusing on the development of a Small Language Model (SLM) using drug package inserts.

## Project Structure & Orchestration

This project adopts a modular architecture where tasks can be executed in two primary ways:

1. **CLI (Typer):** Individual modules (like the ANVISA scraper) act as standalone scripts with command-line interfaces for granular testing and execution.
2. **Dagster:** The central orchestrator that manages complex pipelines, dependencies, and asset materialization.

While a `Makefile` is present for some shortcuts, the primary entry points are the Python modules themselves or the Dagster UI.
