#!/usr/bin/env python3
"""
Bayes MCP Server Implementation
Provides MCP interface for Bayesian inference and statistical analysis
"""

import asyncio
import json
import math
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio


class BayesianCalculator:
    """Bayesian inference calculator"""

    @staticmethod
    def bayes_theorem(prior: float, likelihood: float, evidence: float) -> float:
        """Calculate posterior probability using Bayes' theorem"""
        if evidence == 0:
            raise ValueError("Evidence cannot be zero")
        return (prior * likelihood) / evidence

    @staticmethod
    def update_belief(prior: float, likelihood_true: float, likelihood_false: float) -> float:
        """Update belief given new evidence"""
        evidence = (prior * likelihood_true) + ((1 - prior) * likelihood_false)
        return BayesianCalculator.bayes_theorem(prior, likelihood_true, evidence)

    @staticmethod
    def calculate_credible_interval(samples: List[float], credibility: float = 0.95) -> Dict[str, float]:
        """Calculate Bayesian credible interval"""
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        alpha = 1 - credibility
        lower_idx = int(alpha / 2 * n)
        upper_idx = int((1 - alpha / 2) * n)

        return {
            "lower": sorted_samples[lower_idx],
            "upper": sorted_samples[upper_idx],
            "median": sorted_samples[n // 2],
            "mean": sum(samples) / n
        }

    @staticmethod
    def binomial_beta_update(alpha: float, beta: float, successes: int, failures: int) -> Dict[str, float]:
        """Update Beta distribution parameters with binomial data"""
        new_alpha = alpha + successes
        new_beta = beta + failures

        # Calculate posterior statistics
        mean = new_alpha / (new_alpha + new_beta)
        mode = (new_alpha - 1) / (new_alpha + new_beta - 2) if new_alpha > 1 and new_beta > 1 else None
        variance = (new_alpha * new_beta) / ((new_alpha + new_beta)**2 * (new_alpha + new_beta + 1))

        return {
            "alpha": new_alpha,
            "beta": new_beta,
            "mean": mean,
            "mode": mode,
            "variance": variance,
            "std_dev": math.sqrt(variance)
        }


class MockMCMCSampler:
    """Mock MCMC sampler for demonstration"""

    @staticmethod
    async def sample(model: str, iterations: int, burn_in: int, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform mock MCMC sampling"""
        await asyncio.sleep(0.1)  # Simulate computation time

        # Generate mock samples
        import random
        random.seed(42)  # For reproducibility

        samples = {
            "parameter_1": [random.gauss(0, 1) for _ in range(iterations - burn_in)],
            "parameter_2": [random.gauss(2, 0.5) for _ in range(iterations - burn_in)]
        }

        # Calculate statistics
        stats = {}
        for param, values in samples.items():
            stats[param] = {
                "mean": sum(values) / len(values),
                "std": math.sqrt(sum((x - sum(values)/len(values))**2 for x in values) / len(values)),
                "min": min(values),
                "max": max(values)
            }

        return {
            "model": model,
            "iterations": iterations,
            "burn_in": burn_in,
            "effective_samples": iterations - burn_in,
            "parameters": stats,
            "convergence": {
                "r_hat": 1.01,  # Mock Gelman-Rubin statistic
                "effective_sample_size": iterations - burn_in
            }
        }


class BayesMCPServer:
    """Bayes MCP Server implementation"""

    def __init__(self):
        self.server = Server("bayes-mcp")
        self.calculator = BayesianCalculator()
        self.sampler = MockMCMCSampler()
        self._initialized = False

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[types.TextContent]:
            return await self._handle_tool_call(name, arguments or {})

    def _get_tools(self) -> List[types.Tool]:
        """Define available Bayesian analysis tools"""
        return [
            types.Tool(
                name="bayes_calculate_posterior",
                description="Calculate posterior probability using Bayes' theorem",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prior": {
                            "type": "number",
                            "description": "Prior probability (0-1)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "likelihood": {
                            "type": "number",
                            "description": "Likelihood P(evidence|hypothesis)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "evidence": {
                            "type": "number",
                            "description": "Evidence probability P(evidence)",
                            "minimum": 0,
                            "maximum": 1
                        }
                    },
                    "required": ["prior", "likelihood", "evidence"]
                }
            ),
            types.Tool(
                name="bayes_update_belief",
                description="Update belief with new evidence using Bayesian updating",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prior": {
                            "type": "number",
                            "description": "Prior belief probability (0-1)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "likelihood_true": {
                            "type": "number",
                            "description": "P(evidence|hypothesis is true)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "likelihood_false": {
                            "type": "number",
                            "description": "P(evidence|hypothesis is false)",
                            "minimum": 0,
                            "maximum": 1
                        }
                    },
                    "required": ["prior", "likelihood_true", "likelihood_false"]
                }
            ),
            types.Tool(
                name="bayes_mcmc_sample",
                description="Perform MCMC sampling for parameter estimation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Model name or description"
                        },
                        "iterations": {
                            "type": "integer",
                            "description": "Number of MCMC iterations",
                            "minimum": 100,
                            "default": 10000
                        },
                        "burn_in": {
                            "type": "integer",
                            "description": "Number of burn-in iterations to discard",
                            "minimum": 0,
                            "default": 1000
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Model parameters and priors"
                        }
                    },
                    "required": ["model"]
                }
            ),
            types.Tool(
                name="bayes_beta_binomial",
                description="Update Beta-Binomial conjugate prior with observed data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "alpha": {
                            "type": "number",
                            "description": "Beta distribution alpha parameter (prior)",
                            "minimum": 0,
                            "default": 1
                        },
                        "beta": {
                            "type": "number",
                            "description": "Beta distribution beta parameter (prior)",
                            "minimum": 0,
                            "default": 1
                        },
                        "successes": {
                            "type": "integer",
                            "description": "Number of observed successes",
                            "minimum": 0
                        },
                        "failures": {
                            "type": "integer",
                            "description": "Number of observed failures",
                            "minimum": 0
                        }
                    },
                    "required": ["successes", "failures"]
                }
            ),
            types.Tool(
                name="bayes_credible_interval",
                description="Calculate Bayesian credible interval from samples",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "samples": {
                            "type": "array",
                            "description": "Array of sample values",
                            "items": {"type": "number"}
                        },
                        "credibility": {
                            "type": "number",
                            "description": "Credibility level (e.g., 0.95 for 95%)",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.95
                        }
                    },
                    "required": ["samples"]
                }
            ),
            types.Tool(
                name="bayes_hypothesis_test",
                description="Perform Bayesian hypothesis testing",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "null_prior": {
                            "type": "number",
                            "description": "Prior probability for null hypothesis",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.5
                        },
                        "alternative_prior": {
                            "type": "number",
                            "description": "Prior probability for alternative hypothesis",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.5
                        },
                        "bayes_factor": {
                            "type": "number",
                            "description": "Observed Bayes factor (evidence ratio)",
                            "minimum": 0
                        }
                    },
                    "required": ["bayes_factor"]
                }
            ),
            types.Tool(
                name="bayes_health_check",
                description="Check Bayes MCP server status",
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
            if name == "bayes_calculate_posterior":
                result = await self._calculate_posterior(arguments)
            elif name == "bayes_update_belief":
                result = await self._update_belief(arguments)
            elif name == "bayes_mcmc_sample":
                result = await self._mcmc_sample(arguments)
            elif name == "bayes_beta_binomial":
                result = await self._beta_binomial_update(arguments)
            elif name == "bayes_credible_interval":
                result = await self._credible_interval(arguments)
            elif name == "bayes_hypothesis_test":
                result = await self._hypothesis_test(arguments)
            elif name == "bayes_health_check":
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

    async def _calculate_posterior(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate posterior probability"""
        prior = args.get("prior")
        likelihood = args.get("likelihood")
        evidence = args.get("evidence")

        posterior = self.calculator.bayes_theorem(prior, likelihood, evidence)

        return {
            "status": "success",
            "calculation": {
                "prior": prior,
                "likelihood": likelihood,
                "evidence": evidence,
                "posterior": posterior,
                "formula": "P(H|E) = P(E|H) * P(H) / P(E)"
            }
        }

    async def _update_belief(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update belief with new evidence"""
        prior = args.get("prior")
        likelihood_true = args.get("likelihood_true")
        likelihood_false = args.get("likelihood_false")

        posterior = self.calculator.update_belief(prior, likelihood_true, likelihood_false)

        return {
            "status": "success",
            "update": {
                "prior_belief": prior,
                "posterior_belief": posterior,
                "belief_change": posterior - prior,
                "evidence_strength": likelihood_true / likelihood_false if likelihood_false > 0 else float('inf')
            }
        }

    async def _mcmc_sample(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform MCMC sampling"""
        model = args.get("model")
        iterations = args.get("iterations", 10000)
        burn_in = args.get("burn_in", 1000)
        parameters = args.get("parameters", {})

        result = await self.sampler.sample(model, iterations, burn_in, parameters)

        return {
            "status": "success",
            "sampling": result
        }

    async def _beta_binomial_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update Beta-Binomial conjugate prior"""
        alpha = args.get("alpha", 1)
        beta = args.get("beta", 1)
        successes = args.get("successes")
        failures = args.get("failures")

        result = self.calculator.binomial_beta_update(alpha, beta, successes, failures)

        return {
            "status": "success",
            "posterior": result,
            "prior": {
                "alpha": alpha,
                "beta": beta,
                "mean": alpha / (alpha + beta)
            },
            "data": {
                "successes": successes,
                "failures": failures,
                "total": successes + failures
            }
        }

    async def _credible_interval(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate credible interval"""
        samples = args.get("samples")
        credibility = args.get("credibility", 0.95)

        if not samples or len(samples) == 0:
            raise ValueError("Samples array cannot be empty")

        interval = self.calculator.calculate_credible_interval(samples, credibility)

        return {
            "status": "success",
            "credible_interval": interval,
            "credibility": credibility,
            "sample_size": len(samples)
        }

    async def _hypothesis_test(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform Bayesian hypothesis testing"""
        null_prior = args.get("null_prior", 0.5)
        alternative_prior = args.get("alternative_prior", 0.5)
        bayes_factor = args.get("bayes_factor")

        # Normalize priors
        total_prior = null_prior + alternative_prior
        null_prior = null_prior / total_prior
        alternative_prior = alternative_prior / total_prior

        # Calculate posterior probabilities
        null_posterior = null_prior / (null_prior + alternative_prior * bayes_factor)
        alternative_posterior = 1 - null_posterior

        # Interpret Bayes factor
        if bayes_factor < 1/10:
            interpretation = "Strong evidence for null hypothesis"
        elif bayes_factor < 1/3:
            interpretation = "Moderate evidence for null hypothesis"
        elif bayes_factor < 1:
            interpretation = "Weak evidence for null hypothesis"
        elif bayes_factor < 3:
            interpretation = "Weak evidence for alternative hypothesis"
        elif bayes_factor < 10:
            interpretation = "Moderate evidence for alternative hypothesis"
        else:
            interpretation = "Strong evidence for alternative hypothesis"

        return {
            "status": "success",
            "hypothesis_test": {
                "bayes_factor": bayes_factor,
                "interpretation": interpretation,
                "null_posterior": null_posterior,
                "alternative_posterior": alternative_posterior,
                "posterior_odds": alternative_posterior / null_posterior if null_posterior > 0 else float('inf')
            }
        }

    async def _health_check(self) -> Dict[str, Any]:
        """Check server health"""
        return {
            "status": "healthy",
            "service": "bayes-mcp",
            "version": "1.0.0",
            "capabilities": [
                "bayesian_inference",
                "mcmc_sampling",
                "hypothesis_testing",
                "conjugate_priors",
                "credible_intervals"
            ],
            "timestamp": datetime.now().isoformat()
        }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="bayes-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = BayesMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
