"""Modo comparativo manual vs mecanizado — extracted from scheduler_core."""

from .comparativo_mec import (
    _atividades_com_mecanizado_disponivel,
    _cadastrar_recurso_mecanizado_externo,
    _formatar_substituicao_comparativo,
)
from .constants import CT317_HARDCODE_HH_BASE
from .ui import (
    BL,
    C,
    DM,
    G,
    R,
    RS,
    Y,
    aviso,
    confirmar,
    escolha,
    esperar,
    ok,
    selecionar_paginado,
    sub,
)


def _configurar_modo_comparativo(atividades_reais, _batch):
    # MODO COMPARATIVO: MANUAL vs MECANIZADO
    modo_comparativo = False
    substituicoes_comparativo = {}


    if not _batch:
        # Verificar se há atividades com equivalente mecanizado
        pares_mecanizaveis = _atividades_com_mecanizado_disponivel(atividades_reais)
        if atividades_reais:
            sub()
            print(C + BL + " MODO COMPARATIVO MANUAL vs MECANIZADO" + RS)
            if pares_mecanizaveis:
                print(
                    DM
                    + f" Detectadas {len(pares_mecanizaveis)} atividade(s) com equivalente mecanizado."
                    + RS
                )
            else:
                print(
                    DM
                    + " Nenhuma sugestao automatica encontrada; use modo manual [2] ou recurso externo [3]."
                    + RS
                )

            if confirmar("Deseja executar comparativo MANUAL vs MECANIZADO?", default=False):
                modo_comparativo = True
                # Loop para permitir voltar entre modos
                while True:
                    sub()
                    print(G + " [1] Usar sugestões automáticas (detecção por nome)" + RS)
                    print(G + " [2] Escolher manualmente do catálogo completo" + RS)
                    print(G + " [3] Cadastrar recurso mecanizado externo" + RS)
                    print(R + " [0] Cancelar comparativo" + RS)
                    print(DM + "    (opcão 2 permite escolher QUALQUER atividade mecanizada)" + RS)
                    sub()
                    modo_escolha = escolha("Opção [1/2/3/0]", "1")

                    if modo_escolha == "0":
                        modo_comparativo = False
                        substituicoes_comparativo = {}
                        aviso("Modo comparativo cancelado. Continuando com modo normal.")
                        break

                    if modo_escolha == "1":
                        # MODO AUTOMÁTICO
                        if not pares_mecanizaveis:
                            aviso("Nao ha sugestoes automaticas para esta fazenda. Use [2] ou [3].")
                            continue
                        sub()
                        print(G + " Atividades detectadas automaticamente:" + RS)
                        print()

                        # Mostrar lista numerada
                        for i, (manual, mec) in enumerate(pares_mecanizaveis, 1):
                            print(f" {Y}{i:2}{RS}. {manual}")
                            print(f" {DM}→{RS} {C}{mec}{RS}")
                        print()

                        sub()
                        print(DM + "Digite os números das atividades para trocar (ex: 1,3,5)" + RS)
                        print(DM + "ou ENTER para TODAS, ou 0 para VOLTAR ao menu anterior" + RS)
                        escolha_val = escolha("Escolha")

                        # Verificar se quer voltar
                        if escolha_val == "0":
                            continue # Volta ao início do while loop

                        indices_trocar = []
                        if escolha_val:
                            try:
                                # Parse lista de números
                                for parte in escolha_val.split(","):
                                    idx = int(parte.strip()) - 1
                                    if 0 <= idx < len(pares_mecanizaveis):
                                        indices_trocar.append(idx)
                            except ValueError:
                                aviso("Entrada inválida. Usando TODAS as atividades.")
                                indices_trocar = list(range(len(pares_mecanizaveis)))
                        else:
                            # ENTER = todas
                            indices_trocar = list(range(len(pares_mecanizaveis)))

                        # Construir dicionário de substituições
                        for idx in indices_trocar:
                            manual, mec = pares_mecanizaveis[idx]
                            substituicoes_comparativo[manual] = mec

                        if substituicoes_comparativo:
                            ok(f"Selecionadas {len(substituicoes_comparativo)} substituição(ões) para comparativo.")
                            break  # Sai do loop - seleção concluída
                        else:
                            aviso("Nenhuma atividade selecionada. Voltando ao menu.")
                            continue
                    if modo_escolha == "2":
                        # MODO MANUAL: Mostrar todas as atividades mecanizadas disponíveis
                        modo_manual_ativo = True
                        historico_substituicoes_manual = []
                        while modo_manual_ativo:
                            sub()
                            print(C + BL + " CATÁLOGO DE ATIVIDADES MECANIZADAS DISPONÍVEIS" + RS)
                            print(DM + " (todas as atividades com rendimento HM > 0)" + RS)
                            sub()

                            atividades_mecanizadas = []
                            for atv_nome, dados in CT317_HARDCODE_HH_BASE.items():
                                if dados.get("rendimento_hm", 0) > 0:
                                    atividades_mecanizadas.append((atv_nome, dados.get("rendimento_hm", 0)))

                            atividades_mecanizadas.sort(key=lambda x: x[0])

                            for i, (atv_nome, hm_val) in enumerate(atividades_mecanizadas, 1):
                                print(f" {Y}{i:2}{RS}. {atv_nome[:55]:<55} {C}(HM={hm_val:.2f}){RS}")

                            sub()
                            print(G + f"Total: {len(atividades_mecanizadas)} atividades mecanizadas" + RS)
                            print()
                            print(DM + "Escolha uma atividade mecanizada (ou 0 para voltar):" + RS)
                            print(DM + "Comandos: [L] listar substituições atuais | [U] desfazer última | [A] ver sugestões automáticas" + RS)

                            escolha_mec = escolha("Número (0 para voltar ao menu)")
                            cmd_mec = escolha_mec.upper()
                            if cmd_mec == "0":
                                break

                            if cmd_mec == "L":
                                if substituicoes_comparativo:
                                    sub()
                                    print(G + BL + " SUBSTITUIÇÕES ATUAIS" + RS)
                                    for i, (manual, mec) in enumerate(substituicoes_comparativo.items(), 1):
                                        print(f" {Y}{i:2}{RS}. {manual}")
                                        print(f"    {DM}→{RS} {C}{_formatar_substituicao_comparativo(mec)}{RS}")
                                else:
                                    aviso("Nenhuma substituição selecionada até agora.")
                                continue

                            if cmd_mec == "U":
                                if historico_substituicoes_manual:
                                    atividade_desfazer, valor_anterior = historico_substituicoes_manual.pop()
                                    if valor_anterior is None:
                                        valor_removido = substituicoes_comparativo.pop(atividade_desfazer, None)
                                        if valor_removido is not None:
                                            ok(
                                                "Desfeito: "
                                                + f"{atividade_desfazer[:40]}..."
                                                + " removido da lista de substituições."
                                            )
                                        else:
                                            aviso("Nada para desfazer neste item.")
                                    else:
                                        substituicoes_comparativo[atividade_desfazer] = valor_anterior
                                        ok(
                                            "Desfeito: "
                                            + f"{atividade_desfazer[:40]}..."
                                            + " restaurado para a seleção anterior."
                                        )
                                else:
                                    aviso("Nao ha substituições recentes para desfazer.")
                                continue

                            if cmd_mec == "A":
                                sub()
                                print(C + BL + " SUGESTÕES AUTOMÁTICAS (MANUAL -> MECANIZADA)" + RS)
                                if pares_mecanizaveis:
                                    print()
                                    for i, (manual, mec) in enumerate(pares_mecanizaveis, 1):
                                        print(f" {Y}{i:2}{RS}. {manual}")
                                        print(f"    {DM}→{RS} {C}{_formatar_substituicao_comparativo(mec)}{RS}")
                                else:
                                    aviso("Nao ha sugestões automáticas para esta fazenda.")
                                sub()
                                esperar("ENTER para voltar ao catálogo manual")
                                continue

                            if not escolha_mec:
                                continue

                            try:
                                idx_mec = int(escolha_mec) - 1
                                if 0 <= idx_mec < len(atividades_mecanizadas):
                                    atividade_mecanizada_escolhida = atividades_mecanizadas[idx_mec][0]

                                    sub()
                                    print(C + " Atividades MANUAIS na fazenda:" + RS)
                                    for i, atv_manual in enumerate(atividades_reais, 1):
                                        print(f" {Y}{i:2}{RS}. {atv_manual}")

                                    print()
                                    print(DM + f"Qual atividade substituir por '{atividade_mecanizada_escolhida}'?" + RS)
                                    escolha_manual = escolha("Número da atividade manual (0 para cancelar)")

                                    if escolha_manual == "0":
                                        continue

                                    try:
                                        idx_manual = int(escolha_manual) - 1
                                        if 0 <= idx_manual < len(atividades_reais):
                                            atividade_manual_escolhida = atividades_reais[idx_manual]
                                            valor_anterior = substituicoes_comparativo.get(atividade_manual_escolhida)
                                            if valor_anterior is not None:
                                                print()
                                                print(
                                                    Y
                                                    + "  Esta atividade já possui substituição:"
                                                    + RS
                                                )
                                                print(
                                                    DM
                                                    + f"  {atividade_manual_escolhida}"
                                                    + RS
                                                )
                                                print(
                                                    DM
                                                    + f"  atual: {_formatar_substituicao_comparativo(valor_anterior)}"
                                                    + RS
                                                )
                                                print(
                                                    DM
                                                    + f"  nova : {_formatar_substituicao_comparativo(atividade_mecanizada_escolhida)}"
                                                    + RS
                                                )
                                                if not confirmar("Substituir mapeamento existente?", default=True):
                                                    continue

                                            historico_substituicoes_manual.append(
                                                (atividade_manual_escolhida, valor_anterior)
                                            )
                                            substituicoes_comparativo[atividade_manual_escolhida] = atividade_mecanizada_escolhida
                                            ok(f"Adicionado: {atividade_manual_escolhida[:40]}... → {atividade_mecanizada_escolhida[:40]}...")
                                        else:
                                            aviso("Número inválido.")
                                    except ValueError:
                                        aviso("Entrada inválida.")

                                    print()
                                    if not confirmar("Adicionar outra substituição manual?", default=False):
                                        modo_manual_ativo = False
                                else:
                                    aviso("Número inválido.")
                            except ValueError:
                                aviso("Entrada inválida.")

                        if substituicoes_comparativo:
                            ok(f"Selecionadas {len(substituicoes_comparativo)} substituição(ões) para comparativo.")
                            sub()
                            print(G + " Resumo das substituições:" + RS)
                            for manual, mec in substituicoes_comparativo.items():
                                print(f" • {manual}")
                                print(f" → {C}{_formatar_substituicao_comparativo(mec)}{RS}")
                            sub()
                            esperar("ENTER para continuar")
                            break

                        aviso("Nenhuma substituição selecionada. Voltando ao menu.")
                        continue

                    if modo_escolha == "3":
                        # MODO EXTERNO: cadastrar recurso mecanizado fora do CT e ligar em uma atividade manual.
                        modo_externo_ativo = True
                        while modo_externo_ativo:
                            sub()
                            print(C + BL + " CADASTRAR RECURSO MECANIZADO EXTERNO" + RS)
                            print(DM + " Ex.: Navu, trator alugado, drone, serviço terceirizado." + RS)
                            sub()
                            idx_manual = selecionar_paginado("ATIVIDADE MANUAL A SUBSTITUIR", atividades_reais)
                            if idx_manual < 0:
                                break
                            atividade_manual_escolhida = atividades_reais[idx_manual]
                            recurso_custom = _cadastrar_recurso_mecanizado_externo(
                                atividade_manual_escolhida
                            )
                            if recurso_custom:
                                substituicoes_comparativo[atividade_manual_escolhida] = recurso_custom
                                ok(
                                    f"Adicionado: {atividade_manual_escolhida[:40]}... → {recurso_custom['atividade_mecanizada'][:40]}..."
                                )
                            if not confirmar("Adicionar outro recurso externo?", default=False):
                                modo_externo_ativo = False

                        if substituicoes_comparativo:
                            ok(f"Selecionadas {len(substituicoes_comparativo)} substituição(ões) para comparativo.")
                            sub()
                            print(G + " Resumo das substituições:" + RS)
                            for manual, mec in substituicoes_comparativo.items():
                                print(f" • {manual[:50]}...")
                                print(f" → {C}{_formatar_substituicao_comparativo(mec)}{RS}")
                            sub()
                            esperar("ENTER para continuar")
                            break

                        aviso("Nenhum recurso externo foi vinculado. Voltando ao menu.")
                        continue

                    aviso("Opcao invalida. Use 1, 2, 3 ou 0.")
                    continue

    return modo_comparativo, substituicoes_comparativo
