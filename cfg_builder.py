"""Construa um CFG auxiliar por função, preservando os nós da AST."""

from __future__ import annotations

import load_previous  # Disponibiliza os módulos das etapas anteriores.

from ast_nodes import (
    Assignment, Block, BoolLiteral, CallStmt, FunctionDecl, IfStmt, PrintStmt,
    ReturnStmt, Stmt, VarDecl, WhileStmt,
)
from cfg import BlockId, Branch, CFG, Jump, Return, ScopeExit


class CFGBuilder:
    def build(self, function: FunctionDecl) -> CFG:
        self.cfg = CFG(function)
        body_entry = self.cfg.new_block()
        self.cfg.terminate(self.cfg.entry, Jump(body_entry.id))
        continuation = self._build_block(function.body, body_entry.id)
        if continuation is not None:
            self.cfg.terminate(continuation, Jump(self.cfg.fallthrough_exit))
        return self.cfg

    def _build_block(self, block: Block, current: BlockId) -> BlockId | None:
        """Percorra um bloco da AST e devolva sua continuação normal.

        `current` identifica um bloco básico aberto. Comandos sequenciais
        permanecem nele. Comandos de controle podem mudar a continuação.
        None indica que os caminhos deste bloco não alcançam o próximo comando.
        """

        for statement in block.statements:
            current = self._build_statement(statement, current)
            if current is None:
                return None

        self.cfg.blocks[current].operations.append(ScopeExit(block.metadata["scope"]))
        return current

    def _build_statement(self, statement: Stmt, current: BlockId) -> BlockId | None:
        """incorpora um comando ao cfg e devolve sua continuacao normal."""

        if isinstance(statement, Block):
            return self._build_block(statement, current)
        if isinstance(statement, IfStmt):
            return self._build_if(statement, current)
        if isinstance(statement, WhileStmt):
            return self._build_while(statement, current)
        if isinstance(statement, ReturnStmt):
            self.cfg.terminate(current, Return(statement))
            return None
        if isinstance(statement, (VarDecl, Assignment, PrintStmt, CallStmt)):
            self.cfg.blocks[current].operations.append(statement)
            return current
        raise TypeError(f"comando desconhecido: {type(statement).__name__}")

    def _build_if(self, statement: IfStmt, current: BlockId) -> BlockId | None:
        """constroi os ramos e junta os caminhos que continuam."""

        then_entry = self.cfg.new_block().id
        else_entry = self.cfg.new_block().id
        self.cfg.terminate(current, Branch(statement.condition, then_entry, else_entry))

        then_end = self._build_block(statement.then_block, then_entry)
        else_end = else_entry
        if statement.else_block is not None:
            else_end = self._build_block(statement.else_block, else_entry)

        if then_end is None and else_end is None:
            return None

        continuation = self.cfg.new_block().id
        for branch_end in (then_end, else_end):
            if branch_end is not None:
                self.cfg.terminate(branch_end, Jump(continuation))
        return continuation

    def _build_while(self, statement: WhileStmt, current: BlockId) -> BlockId | None:
        """constroi o teste, o corpo e a saida normal do laco."""

        test = self.cfg.new_block().id
        body_entry = self.cfg.new_block().id
        self.cfg.terminate(current, Jump(test))

        continuation = None
        if isinstance(statement.condition, BoolLiteral) and statement.condition.value:
            self.cfg.terminate(test, Jump(body_entry))
        else:
            continuation = self.cfg.new_block().id
            self.cfg.terminate(
                test, Branch(statement.condition, body_entry, continuation),
            )

        body_end = self._build_block(statement.body, body_entry)
        if body_end is not None:
            self.cfg.terminate(body_end, Jump(test))
        return continuation
