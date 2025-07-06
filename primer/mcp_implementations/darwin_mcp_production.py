#!/usr/bin/env python3
"""
Darwin MCP Server - Production Implementation
Genetic Algorithm Optimization Platform Integration
"""

import asyncio
import json
import os
import sys
import math
import random
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Darwin genetic algorithm implementation
@dataclass
class Individual:
    """Represents an individual in the genetic algorithm population"""
    genome: List[float]
    fitness: Optional[float] = None
    generation: int = 0
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"ind_{datetime.now().timestamp():.0f}_{random.randint(1000, 9999)}"


@dataclass
class Population:
    """Represents a population in the genetic algorithm"""
    individuals: List[Individual]
    generation: int = 0
    best_fitness: float = 0.0
    average_fitness: float = 0.0
    id: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"pop_{datetime.now().timestamp():.0f}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class GeneticAlgorithm:
    """Core genetic algorithm implementation"""

    def __init__(self):
        self.populations: Dict[str, Population] = {}
        self.fitness_functions: Dict[str, callable] = {
            "sphere": self._sphere_function,
            "rastrigin": self._rastrigin_function,
            "rosenbrock": self._rosenbrock_function,
            "ackley": self._ackley_function
        }

    def _sphere_function(self, genome: List[float]) -> float:
        """Sphere function - simple quadratic optimization problem"""
        return -sum(x**2 for x in genome)

    def _rastrigin_function(self, genome: List[float]) -> float:
        """Rastrigin function - highly multimodal function"""
        n = len(genome)
        A = 10
        return -(A * n + sum(x**2 - A * np.cos(2 * np.pi * x) for x in genome))

    def _rosenbrock_function(self, genome: List[float]) -> float:
        """Rosenbrock function - valley-shaped function"""
        return -sum(100 * (genome[i+1] - genome[i]**2)**2 + (1 - genome[i])**2
                   for i in range(len(genome) - 1))

    def _ackley_function(self, genome: List[float]) -> float:
        """Ackley function - multimodal with many local optima"""
        n = len(genome)
        sum1 = sum(x**2 for x in genome)
        sum2 = sum(np.cos(2 * np.pi * x) for x in genome)
        return (20 + np.e - 20 * np.exp(-0.2 * np.sqrt(sum1 / n)) -
                np.exp(sum2 / n))

    def create_population(self, size: int, genome_length: int,
                         gene_min: float = -5.0, gene_max: float = 5.0) -> Population:
        """Create a new population with random individuals"""
        individuals = []
        for _ in range(size):
            genome = [random.uniform(gene_min, gene_max) for _ in range(genome_length)]
            individuals.append(Individual(genome=genome))

        population = Population(individuals=individuals)
        self.populations[population.id] = population
        return population

    def evaluate_fitness(self, population_id: str, fitness_function: str) -> Population:
        """Evaluate fitness for all individuals in a population"""
        if population_id not in self.populations:
            raise ValueError(f"Population {population_id} not found")

        population = self.populations[population_id]
        fitness_func = self.fitness_functions.get(fitness_function, self._sphere_function)

        total_fitness = 0
        best_fitness = float('-inf')

        for individual in population.individuals:
            individual.fitness = fitness_func(individual.genome)
            total_fitness += individual.fitness
            if individual.fitness > best_fitness:
                best_fitness = individual.fitness

        population.best_fitness = best_fitness
        population.average_fitness = total_fitness / len(population.individuals)

        return population

    def selection(self, population: Population, num_parents: int) -> List[Individual]:
        """Tournament selection of parents"""
        parents = []
        tournament_size = 3

        for _ in range(num_parents):
            tournament = random.sample(population.individuals, tournament_size)
            winner = max(tournament, key=lambda x: x.fitness or float('-inf'))
            parents.append(winner)

        return parents

    def crossover(self, parent1: Individual, parent2: Individual,
                  crossover_rate: float = 0.8) -> Tuple[Individual, Individual]:
        """Single-point crossover between two parents"""
        if random.random() > crossover_rate:
            return parent1, parent2

        genome_length = len(parent1.genome)
        crossover_point = random.randint(1, genome_length - 1)

        child1_genome = parent1.genome[:crossover_point] + parent2.genome[crossover_point:]
        child2_genome = parent2.genome[:crossover_point] + parent1.genome[crossover_point:]

        return (Individual(genome=child1_genome, generation=parent1.generation + 1),
                Individual(genome=child2_genome, generation=parent1.generation + 1))

    def mutate(self, individual: Individual, mutation_rate: float = 0.1,
               mutation_strength: float = 0.5) -> Individual:
        """Gaussian mutation of an individual"""
        mutated_genome = individual.genome.copy()

        for i in range(len(mutated_genome)):
            if random.random() < mutation_rate:
                mutated_genome[i] += random.gauss(0, mutation_strength)
                # Optionally clamp to bounds
                mutated_genome[i] = max(-10, min(10, mutated_genome[i]))

        return Individual(
            genome=mutated_genome,
            generation=individual.generation,
            fitness=None
        )

    def evolve_generation(self, population_id: str, fitness_function: str,
                         crossover_rate: float = 0.8, mutation_rate: float = 0.1,
                         elitism_count: int = 2) -> Population:
        """Evolve one generation of the population"""
        if population_id not in self.populations:
            raise ValueError(f"Population {population_id} not found")

        population = self.populations[population_id]

        # Ensure fitness is evaluated
        if population.individuals[0].fitness is None:
            self.evaluate_fitness(population_id, fitness_function)

        # Sort by fitness (descending)
        sorted_individuals = sorted(population.individuals,
                                  key=lambda x: x.fitness or float('-inf'),
                                  reverse=True)

        new_individuals = []

        # Elitism - keep best individuals
        for i in range(min(elitism_count, len(sorted_individuals))):
            new_individuals.append(sorted_individuals[i])

        # Generate rest of population
        while len(new_individuals) < len(population.individuals):
            # Selection
            parents = self.selection(population, 2)

            # Crossover
            child1, child2 = self.crossover(parents[0], parents[1], crossover_rate)

            # Mutation
            child1 = self.mutate(child1, mutation_rate)
            child2 = self.mutate(child2, mutation_rate)

            new_individuals.extend([child1, child2])

        # Trim to population size
        new_individuals = new_individuals[:len(population.individuals)]

        # Create new population
        new_population = Population(
            individuals=new_individuals,
            generation=population.generation + 1,
            id=population_id
        )

        # Evaluate fitness of new population
        self.populations[population_id] = new_population
        return self.evaluate_fitness(population_id, fitness_function)


class DarwinMCPServer:
    """Darwin MCP Server implementation"""

    def __init__(self):
        self.server = Server("darwin-mcp")
        self.ga = GeneticAlgorithm()
        self._initialized = False

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[types.TextContent]:
            return await self._handle_tool_call(name, arguments or {})

    def _get_tools(self) -> List[types.Tool]:
        """Define available Darwin genetic algorithm tools"""
        return [
            types.Tool(
                name="darwin_create_population",
                description="Create a new population for genetic algorithm optimization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "population_size": {
                            "type": "integer",
                            "description": "Number of individuals in the population",
                            "minimum": 10,
                            "maximum": 10000,
                            "default": 100
                        },
                        "genome_length": {
                            "type": "integer",
                            "description": "Length of the genome (number of genes)",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 10
                        },
                        "gene_min": {
                            "type": "number",
                            "description": "Minimum value for genes",
                            "default": -5.0
                        },
                        "gene_max": {
                            "type": "number",
                            "description": "Maximum value for genes",
                            "default": 5.0
                        }
                    },
                    "required": ["population_size", "genome_length"]
                }
            ),
            types.Tool(
                name="darwin_evaluate_fitness",
                description="Evaluate fitness of all individuals in a population",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "population_id": {
                            "type": "string",
                            "description": "ID of the population to evaluate"
                        },
                        "fitness_function": {
                            "type": "string",
                            "description": "Fitness function to use",
                            "enum": ["sphere", "rastrigin", "rosenbrock", "ackley"],
                            "default": "sphere"
                        }
                    },
                    "required": ["population_id"]
                }
            ),
            types.Tool(
                name="darwin_evolve",
                description="Run evolution cycles on a population",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "population_id": {
                            "type": "string",
                            "description": "ID of the population to evolve"
                        },
                        "generations": {
                            "type": "integer",
                            "description": "Number of generations to evolve",
                            "minimum": 1,
                            "maximum": 10000,
                            "default": 100
                        },
                        "fitness_function": {
                            "type": "string",
                            "description": "Fitness function to use",
                            "enum": ["sphere", "rastrigin", "rosenbrock", "ackley"],
                            "default": "sphere"
                        },
                        "crossover_rate": {
                            "type": "number",
                            "description": "Probability of crossover",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.8
                        },
                        "mutation_rate": {
                            "type": "number",
                            "description": "Probability of mutation per gene",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.1
                        },
                        "elitism_count": {
                            "type": "integer",
                            "description": "Number of best individuals to preserve",
                            "minimum": 0,
                            "default": 2
                        }
                    },
                    "required": ["population_id"]
                }
            ),
            types.Tool(
                name="darwin_get_best",
                description="Get the best individuals from a population",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "population_id": {
                            "type": "string",
                            "description": "ID of the population"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of best individuals to return",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 5
                        }
                    },
                    "required": ["population_id"]
                }
            ),
            types.Tool(
                name="darwin_get_population_stats",
                description="Get statistics about a population",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "population_id": {
                            "type": "string",
                            "description": "ID of the population"
                        }
                    },
                    "required": ["population_id"]
                }
            ),
            types.Tool(
                name="darwin_list_populations",
                description="List all active populations",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="darwin_crossover",
                description="Perform crossover between two individuals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent1_genome": {
                            "type": "array",
                            "description": "Genome of first parent",
                            "items": {"type": "number"}
                        },
                        "parent2_genome": {
                            "type": "array",
                            "description": "Genome of second parent",
                            "items": {"type": "number"}
                        },
                        "crossover_rate": {
                            "type": "number",
                            "description": "Probability of crossover",
                            "default": 0.8
                        }
                    },
                    "required": ["parent1_genome", "parent2_genome"]
                }
            ),
            types.Tool(
                name="darwin_mutate",
                description="Apply mutation to an individual",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "genome": {
                            "type": "array",
                            "description": "Genome to mutate",
                            "items": {"type": "number"}
                        },
                        "mutation_rate": {
                            "type": "number",
                            "description": "Probability of mutation per gene",
                            "default": 0.1
                        },
                        "mutation_strength": {
                            "type": "number",
                            "description": "Standard deviation of mutation",
                            "default": 0.5
                        }
                    },
                    "required": ["genome"]
                }
            ),
            types.Tool(
                name="darwin_health_check",
                description="Check Darwin MCP server health and status",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle tool execution"""
        try:
            # Route to appropriate handler
            if name == "darwin_create_population":
                result = await self._create_population(arguments)
            elif name == "darwin_evaluate_fitness":
                result = await self._evaluate_fitness(arguments)
            elif name == "darwin_evolve":
                result = await self._evolve(arguments)
            elif name == "darwin_get_best":
                result = await self._get_best(arguments)
            elif name == "darwin_get_population_stats":
                result = await self._get_population_stats(arguments)
            elif name == "darwin_list_populations":
                result = await self._list_populations()
            elif name == "darwin_crossover":
                result = await self._crossover(arguments)
            elif name == "darwin_mutate":
                result = await self._mutate(arguments)
            elif name == "darwin_health_check":
                result = await self._health_check()
            else:
                result = {"error": f"Unknown tool: {name}"}

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "tool": name,
                    "status": "failed"
                }, indent=2)
            )]

    async def _create_population(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new population"""
        population = self.ga.create_population(
            size=args.get("population_size", 100),
            genome_length=args.get("genome_length", 10),
            gene_min=args.get("gene_min", -5.0),
            gene_max=args.get("gene_max", 5.0)
        )

        return {
            "status": "success",
            "population": {
                "id": population.id,
                "size": len(population.individuals),
                "genome_length": len(population.individuals[0].genome),
                "generation": population.generation,
                "created_at": population.created_at
            }
        }

    async def _evaluate_fitness(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate fitness of a population"""
        population_id = args.get("population_id")
        fitness_function = args.get("fitness_function", "sphere")

        population = self.ga.evaluate_fitness(population_id, fitness_function)

        return {
            "status": "success",
            "population": {
                "id": population.id,
                "generation": population.generation,
                "best_fitness": population.best_fitness,
                "average_fitness": population.average_fitness,
                "fitness_function": fitness_function
            }
        }

    async def _evolve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Evolve a population for multiple generations"""
        population_id = args.get("population_id")
        generations = args.get("generations", 100)
        fitness_function = args.get("fitness_function", "sphere")
        crossover_rate = args.get("crossover_rate", 0.8)
        mutation_rate = args.get("mutation_rate", 0.1)
        elitism_count = args.get("elitism_count", 2)

        history = []
        start_time = datetime.now()

        for gen in range(generations):
            population = self.ga.evolve_generation(
                population_id=population_id,
                fitness_function=fitness_function,
                crossover_rate=crossover_rate,
                mutation_rate=mutation_rate,
                elitism_count=elitism_count
            )

            # Record history every 10 generations or on last generation
            if gen % 10 == 0 or gen == generations - 1:
                history.append({
                    "generation": population.generation,
                    "best_fitness": population.best_fitness,
                    "average_fitness": population.average_fitness
                })

        evolution_time = (datetime.now() - start_time).total_seconds()

        # Calculate convergence metrics
        if len(history) > 1:
            initial_best = history[0]["best_fitness"]
            final_best = history[-1]["best_fitness"]
            improvement = final_best - initial_best
            convergence_rate = improvement / generations if generations > 0 else 0
        else:
            convergence_rate = 0

        return {
            "status": "success",
            "evolution": {
                "population_id": population_id,
                "generations_completed": generations,
                "final_generation": population.generation,
                "best_fitness": population.best_fitness,
                "average_fitness": population.average_fitness,
                "convergence_rate": convergence_rate,
                "evolution_time_seconds": evolution_time,
                "history": history
            }
        }

    async def _get_best(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get the best individuals from a population"""
        population_id = args.get("population_id")
        count = args.get("count", 5)

        if population_id not in self.ga.populations:
            raise ValueError(f"Population {population_id} not found")

        population = self.ga.populations[population_id]

        # Sort by fitness
        sorted_individuals = sorted(
            population.individuals,
            key=lambda x: x.fitness or float('-inf'),
            reverse=True
        )[:count]

        best_individuals = []
        for ind in sorted_individuals:
            best_individuals.append({
                "id": ind.id,
                "fitness": ind.fitness,
                "genome": ind.genome,
                "generation": ind.generation
            })

        return {
            "status": "success",
            "best_individuals": best_individuals,
            "population_id": population_id
        }

    async def _get_population_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about a population"""
        population_id = args.get("population_id")

        if population_id not in self.ga.populations:
            raise ValueError(f"Population {population_id} not found")

        population = self.ga.populations[population_id]

        # Calculate fitness statistics
        fitness_values = [ind.fitness for ind in population.individuals if ind.fitness is not None]

        if fitness_values:
            stats = {
                "min_fitness": min(fitness_values),
                "max_fitness": max(fitness_values),
                "mean_fitness": sum(fitness_values) / len(fitness_values),
                "median_fitness": sorted(fitness_values)[len(fitness_values) // 2],
                "std_fitness": np.std(fitness_values) if len(fitness_values) > 1 else 0
            }
        else:
            stats = {
                "min_fitness": None,
                "max_fitness": None,
                "mean_fitness": None,
                "median_fitness": None,
                "std_fitness": None
            }

        return {
            "status": "success",
            "population": {
                "id": population_id,
                "size": len(population.individuals),
                "generation": population.generation,
                "created_at": population.created_at,
                "statistics": stats
            }
        }

    async def _list_populations(self) -> Dict[str, Any]:
        """List all active populations"""
        populations = []

        for pop_id, population in self.ga.populations.items():
            populations.append({
                "id": pop_id,
                "size": len(population.individuals),
                "generation": population.generation,
                "best_fitness": population.best_fitness,
                "average_fitness": population.average_fitness,
                "created_at": population.created_at
            })

        return {
            "status": "success",
            "populations": populations,
            "count": len(populations)
        }

    async def _crossover(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform crossover between two parent genomes"""
        parent1_genome = args.get("parent1_genome")
        parent2_genome = args.get("parent2_genome")
        crossover_rate = args.get("crossover_rate", 0.8)

        parent1 = Individual(genome=parent1_genome)
        parent2 = Individual(genome=parent2_genome)

        child1, child2 = self.ga.crossover(parent1, parent2, crossover_rate)

        return {
            "status": "success",
            "children": [
                {"genome": child1.genome, "id": child1.id},
                {"genome": child2.genome, "id": child2.id}
            ]
        }

    async def _mutate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mutation to a genome"""
        genome = args.get("genome")
        mutation_rate = args.get("mutation_rate", 0.1)
        mutation_strength = args.get("mutation_strength", 0.5)

        individual = Individual(genome=genome)
        mutated = self.ga.mutate(individual, mutation_rate, mutation_strength)

        return {
            "status": "success",
            "original_genome": genome,
            "mutated_genome": mutated.genome,
            "mutations": sum(1 for i in range(len(genome)) if genome[i] != mutated.genome[i])
        }

    async def _health_check(self) -> Dict[str, Any]:
        """Check server health"""
        return {
            "status": "healthy",
            "service": "darwin-mcp",
            "version": "1.0.0",
            "capabilities": [
                "genetic_algorithms",
                "population_evolution",
                "fitness_optimization",
                "crossover_mutation",
                "multi_objective"
            ],
            "fitness_functions": list(self.ga.fitness_functions.keys()),
            "active_populations": len(self.ga.populations),
            "timestamp": datetime.now().isoformat()
        }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="darwin-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = DarwinMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
