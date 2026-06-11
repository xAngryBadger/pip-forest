"use strict";

(function() {
    const API_BASE = '/api/schedule/wizard';
    let currentSession = null;

    function getSessionId() {
        if (!currentSession) {
            currentSession = localStorage.getItem('orca_wizard_session');
            if (!currentSession) {
                currentSession = 'wiz_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
                localStorage.setItem('orca_wizard_session', currentSession);
            }
        }
        return currentSession;
    }

    async function api(endpoint, options = {}) {
        options.headers = options.headers || {};
        options.headers['Content-Type'] = 'application/json';
        options.headers['X-Session-ID'] = getSessionId();
        const res = await fetch(`${API_BASE}${endpoint}`, options);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text}`);
        }
        return options.method === 'DELETE' ? res.ok : res.json();
    }

    function initFarmSearch() {
        const input = document.getElementById('farm-search');
        const suggestions = document.getElementById('farm-suggestions');
        const hiddenId = document.getElementById('farm-id');
    let debounceTimer = null;

        if (!input || !suggestions) return;

        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const q = this.value.trim();
            if (q.length < 2) {
                suggestions.classList.add('hidden');
                return;
            }
            debounceTimer = setTimeout(async () => {
                try {
                    const data = await api(`/farms?q=${encodeURIComponent(q)}`);
                    if (data.farms && data.farms.length > 0) {
                        suggestions.innerHTML = data.farms.map(f => 
                            `<button type="button" class="w-full px-4 py-3 text-left text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 last:border-0" data-farm="${escapeHtml(f)}">${escapeHtml(f)}</button>`
                        ).join('');
                        suggestions.classList.remove('hidden');
                        suggestions.querySelectorAll('button').forEach(btn => {
                            btn.addEventListener('click', function() {
                                const farmName = this.dataset.farm;
                                input.value = farmName;
                                if (hiddenId) hiddenId.value = farmName;
                suggestions.classList.add('hidden');
                onFarmSelected(farmName);
                            });
                        });
                    } else {
                        suggestions.innerHTML = '<div class="p-4 text-gray-500 dark:text-gray-400 text-center">Nenhuma fazenda encontrada</div>';
                        suggestions.classList.remove('hidden');
                    }
                } catch (e) {
                    console.error('Farm search error:', e);
                }
            }, 300);
        });

        document.addEventListener('click', function(e) {
            if (!suggestions.contains(e.target) && e.target !== input) {
                suggestions.classList.add('hidden');
            }
        });
}

    async function onFarmSelected(farmName) {
        if (farmName && farmName.length > 0) {
            try {
                const methData = await api(`/methodologies/${encodeURIComponent(farmName)}`);
                const talData = await api(`/talhoes/${encodeURIComponent(farmName)}`);
                renderMethodologies(methData.methodologies || []);
                renderTalhoes(talData.talhoes || []);
            } catch (e) {
                console.error('Error loading farm data:', e);
            }
        }
    }

    function renderMethodologies(methodologies) {
        const container = document.getElementById('methodology-list');
        if (!container) return;
        container.innerHTML = methodologies.map(m => 
            `<label class="flex items-center space-x-2 cursor-pointer p-1">
                <input type="checkbox" name="metodologia_item" value="${escapeHtml(m)}" class="w-4 h-4 text-blue-600 border-gray-300 rounded">
                <span class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(m)}</span>
            </label>`
        ).join('');
    }

    function renderTalhoes(talhoes) {
        const container = document.getElementById('talhao-list');
        if (!container) return;
        container.innerHTML = talhoes.map(t => 
            `<label class="flex items-center space-x-2 cursor-pointer p-1">
                <input type="checkbox" name="talhao_item" value="${escapeHtml(t)}" class="w-4 h-4 text-blue-600 border-gray-300 rounded">
                <span class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(t)}</span>
            </label>`
        ).join('');
    }

    function initMethodologyScope() {
        const radios = document.querySelectorAll('input[name="methodology_scope"]');
        const selectDiv = document.getElementById('methodology-select');
        const filterDiv = document.getElementById('methodology-filter');
        if (!radios.length) return;

        radios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (selectDiv) selectDiv.classList.toggle('hidden', this.value !== 'select');
                if (filterDiv) filterDiv.classList.toggle('hidden', this.value !== 'filter');
            });
        });
    }

function initTalhaoScope() {
    const radios = document.querySelectorAll('input[name="talhao_scope"]');
    const selectDiv = document.getElementById('talhao-select');
    const filterDiv = document.getElementById('talhao-filter');
    if (!radios.length) return;

    radios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (selectDiv) selectDiv.classList.toggle('hidden', this.value !== 'select');
            if (filterDiv) filterDiv.classList.toggle('hidden', this.value !== 'filter');
        });
    });
}

function initMunicipalityFilter() {
    const estadoSelect = document.getElementById('state-filter');
    const munSelect = document.getElementById('municipality-filter');
    if (!estadoSelect || !munSelect) return;
    estadoSelect.addEventListener('change', function() {
        const estado = this.value;
        if (!estado) {
            munSelect.innerHTML = '<option value="">Todos</option>';
            return;
        }
        api(`/municipios?estado=${encodeURIComponent(estado)}`).then(data => {
            munSelect.innerHTML = '<option value="">Todos</option>' + (data.municipios || []).map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
        }).catch(e => console.error('Error loading municipios:', e));
    });
}

function initTeamBuilder() {
        let teamCount = 0;
        const addBtn = document.getElementById('add-team-btn');
        const container = document.getElementById('teams-container');
        const summary = document.getElementById('teams-summary');
        const executoresDisplay = document.getElementById('executores-display') || document.getElementById('total-executores');
        
        function updateTeamCount() {
            const rows = container.querySelectorAll('.team-row');
            teamCount = rows.length;
            updateSummary();
        }

        function createTeamRow(index, data = {}) {
            const div = document.createElement('div');
            div.className = 'team-row p-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center';
            div.innerHTML = `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nome</label>
                    <input type="text" name="turma_nome" value="${escapeHtml(data.nome || 'Turma ' + (index + 1))}" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-base" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Operários</label>
                    <input type="number" name="turma_operarios" value="${data.operarios || 5}" min="1" max="100" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-base" required>
                </div>
                <div class="flex items-end">
                    <button type="button" class="remove-team-btn px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition">Remover</button>
                </div>
            `;
            div.querySelector('.remove-team-btn').addEventListener('click', () => {
                div.remove();
                updateTeamCount();
            });
            div.querySelectorAll('input').forEach(i => i.addEventListener('input', updateSummary));
            return div;
        }

        function updateSummary() {
            const inputs = container.querySelectorAll('input[name="turma_operarios"]');
            const total = Array.from(inputs).reduce((sum, inp) => sum + (parseInt(inp.value) || 0), 0);
            if (summary) {
                document.getElementById('teams-total').textContent = total;
                summary.classList.toggle('hidden', total === 0);
            }
            if (executoresDisplay) {
                executoresDisplay.textContent = parseInt(executoresDisplay.value) || total;
            }
        }

        if (addBtn && container) {
            addBtn.addEventListener('click', () => {
                container.appendChild(createTeamRow(teamCount));
                teamCount++;
                updateSummary();
            });

            container.querySelectorAll('.remove-team-btn').forEach((btn, i) => {
                btn.addEventListener('click', () => {
                    btn.closest('.team-row').remove();
                    updateTeamCount();
                });
            });
            
            // Initialize with at least one row if empty
            if (container.querySelectorAll('.team-row').length === 0) {
                container.appendChild(createTeamRow(0));
                teamCount = 1;
            }
            updateTeamCount();
        }
    }

    function initJornadaInput() {
        const input = document.getElementById('jornada-input');
        if (!input) return;
        
        input.addEventListener('blur', function() {
            let val = this.value.trim();
            if (val.includes(':')) {
                const parts = val.split(':');
                const hours = parseInt(parts[0]) || 0;
                const mins = parseInt(parts[1]) || 0;
                this.value = (hours + mins / 60).toFixed(2);
            } else if (!isNaN(parseFloat(val))) {
                this.value = parseFloat(val).toFixed(2);
            }
        });
    }

    function initActivityAccordions() {
        document.querySelectorAll('.accordion-header').forEach(header => {
            header.addEventListener('click', function() {
                const content = this.nextElementSibling;
                const icon = this.querySelector('svg');
                const isHidden = content.classList.contains('hidden');
                content.classList.toggle('hidden', !isHidden);
                icon.style.transform = isHidden ? 'rotate(180deg)' : '';
                this.setAttribute('aria-expanded', isHidden);
            });
        });

        document.querySelectorAll('.select-all-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const target = document.getElementById(this.dataset.target);
                if (target) target.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
            });
        });

        document.querySelectorAll('.deselect-all-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const target = document.getElementById(this.dataset.target);
                if (target) target.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            });
        });
    }

    function initOrphanHandling() {
        const checkbox = document.querySelector('input[name="auto_assign_orphans"]');
        const target = document.getElementById('orphan-target');
        if (checkbox && target) {
            checkbox.addEventListener('change', function() {
                target.classList.toggle('hidden', !this.checked);
            });
        }
    }

    async function loadActivities() {
        const farmInput = document.querySelector('input[name="farm_name"]');
        if (!farmInput || !farmInput.value) return;

        try {
            const data = await api(`/activities/${encodeURIComponent(farmInput.value)}`);
            const containers = document.querySelectorAll('.activities-grid');
            containers.forEach(container => {
                container.innerHTML = (data.activities || []).map(atv => 
                    `<label class="flex items-center space-x-2 cursor-pointer p-2 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                        <input type="checkbox" name="atividade_vinculos" value="${escapeHtml(atv.atividade)}" class="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500">
                        <span class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(atv.atividade)} <span class="text-gray-500 dark:text-gray-400">(${atv.area_ha} ha)</span></span>
                    </label>`
                ).join('');
            });

            // Also populate external mecanizado activity selector
            const extSelect = document.querySelector('select[name="ext_atividade_substituida"]');
            if (extSelect) {
                extSelect.innerHTML = '<option value="">Selecione...</option>' + 
                    (data.activities || []).map(atv => 
                        `<option value="${escapeHtml(atv.atividade)}">${escapeHtml(atv.atividade)}</option>`
                    ).join('');
            }
        } catch (e) {
            console.error('Error loading activities:', e);
        }
    }

    function initTariffGaps() {
        const checkBtn = document.getElementById('check-gaps-btn');
        if (!checkBtn) return;

        checkBtn.addEventListener('click', async function() {
            try {
                const farmInput = document.querySelector('input[name="farm_name"]');
                if (!farmInput || !farmInput.value) {
                    alert('Selecione uma fazenda primeiro.');
                    return;
                }
                const data = await api(`/tarifas/gaps?farm=${encodeURIComponent(farmInput.value)}`);
                renderGaps(data.gaps || []);
                const count = document.getElementById('gap-count');
                if (count) count.textContent = (data.gaps || []).length;
            } catch (e) {
                console.error('Error checking gaps:', e);
                alert('Erro ao verificar lacunas: ' + e.message);
            }
        });
    }

function renderGaps(gaps) {
    const list = document.getElementById('tariff-gaps-list');
    if (!list) return;
    if (gaps.length === 0) {
        list.innerHTML = '<p class="text-green-600 dark:text-green-400 text-center py-8">Todas as atividades têm tarifa.</p>';
        return;
    }
    list.innerHTML = gaps.map((gap, i) => `
    <div class="p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-red-50 dark:bg-red-900/10" data-gap-key="${escapeHtml(gap.key)}">
        <div class="flex items-start justify-between mb-3">
            <div>
                <h4 class="font-medium text-gray-900 dark:text-gray-100">${escapeHtml(gap.atividade)}</h4>
                <p class="text-sm text-gray-500 dark:text-gray-400">Chave: ${escapeHtml(gap.key)}</p>
            </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">HH/ha</label>
                <input type="number" name="manual_hh" step="0.1" value="8.0" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Preço R$/ha</label>
                <input type="number" name="manual_preco" step="0.01" value="0.0" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Custo R$/h</label>
                <input type="number" name="manual_custo" step="0.01" value="0.0" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            </div>
        </div>
    </div>
    `).join('');
}

    function initComparativoMode() {
        const radios = document.querySelectorAll('input[name="modo_comparativo"]');
        const simpleDiv = document.getElementById('simple-comparativo');
        const multiDiv = document.getElementById('multifactor-config');
        if (!radios.length) return;

        radios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (simpleDiv) simpleDiv.classList.toggle('hidden', this.value !== 'simple');
                if (multiDiv) multiDiv.classList.toggle('hidden', this.value !== 'multi-factor');
            });
        });
    }

    function initExternalMecanizado() {
        const addBtn = document.getElementById('add-external-btn');
        if (!addBtn) return;

        addBtn.addEventListener('click', function() {
            const nome = document.querySelector('input[name="ext_nome"]')?.value || '';
            const prod = document.querySelector('input[name="ext_prod_ha_h"]')?.value || '';
            const custo = document.querySelector('input[name="ext_custo_h"]')?.value || '';
            const atividade = document.querySelector('select[name="ext_atividade_substituida"]')?.value || '';
            
            if (!nome || !prod) {
                alert('Nome e produtividade são obrigatórios.');
                return;
            }

            const list = document.getElementById('external-list');
            const items = document.getElementById('external-items');
            if (!list || !items) return;

            const item = document.createElement('div');
            item.className = 'p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg flex items-start justify-between';
            item.innerHTML = `
                <div>
                    <p class="font-medium text-gray-900 dark:text-gray-100">${escapeHtml(nome)}</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">${prod} ha/h | R$ ${custo}/h | ${escapeHtml(atividade)}</p>
                </div>
                <button type="button" class="text-red-500 hover:text-red-700">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            `;
            item.querySelector('button').addEventListener('click', () => item.remove());
            items.appendChild(item);
            list.classList.remove('hidden');
        });
    }

    function escapeHtml(str) {
        if (str == null) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

function collectAllSteps() {
    const step1 = {
        farm_name: document.querySelector('input[name="farm_name"]')?.value || '',
        farm_id: document.querySelector('input[name="farm_id"]')?.value || '',
        state_filter: document.querySelector('select[name="state_filter"]')?.value || '',
        municipality_filter: document.querySelector('select[name="municipality_filter"]')?.value || '',
        company_filter: document.querySelector('select[name="company_filter"]')?.value || '',
        methodology_scope: document.querySelector('input[name="methodology_scope"]:checked')?.value || 'all',
        metodologias_selected: Array.from(document.querySelectorAll('#methodology-list input:checked')).map(i => i.value),
        talhao_scope: document.querySelector('input[name="talhao_scope"]:checked')?.value || 'all',
        talhoes_selected: Array.from(document.querySelectorAll('#talhao-list input:checked')).map(i => i.value),
        penalidade: parseFloat(document.querySelector('input[name="penalidade"]:checked')?.value || '1.0')
    };
    const turmas = [];
    document.querySelectorAll('.team-row').forEach(row => {
        turmas.push({
            nome: row.querySelector('input[name="turma_nome"]')?.value || '',
            operarios: parseInt(row.querySelector('input[name="turma_operarios"]')?.value || '0'),
            atividades: []
        });
    });
    const step2 = {
        penalidade: step1.penalidade,
        modo_seq: document.querySelector('input[name="modo_seq"]:checked')?.value || 'implantacao',
        usar_bloqueio_global: document.querySelector('input[name="usar_bloqueio_global"]')?.checked ?? true,
        usar_reforco_automatico: document.querySelector('input[name="usar_reforco_automatico"]')?.checked ?? true,
        usar_pool_pos_bloqueio: document.querySelector('input[name="usar_pool_pos_bloqueio"]')?.checked ?? true,
        prazo_meses: parseFloat(document.querySelector('input[name="prazo_meses"]')?.value || '6.0'),
        mes_ref: parseInt(document.querySelector('input[name="mes_ref"]')?.value || '1'),
        ano_ref: parseInt(document.querySelector('input[name="ano_ref"]')?.value || '2026'),
        dia_ref: parseInt(document.querySelector('input[name="dia_ref"]')?.value || '1'),
        data_inicio_txt: document.querySelector('input[name="data_inicio_txt"]')?.value || '',
        data_fim_txt: '',
        jornada: parseFloat(document.querySelector('input[name="jornada"]')?.value || '4.6'),
        executores: parseInt(document.querySelector('input[name="executores"]')?.value || '9'),
        turmas: turmas
    };
    const jornadaRaw = document.querySelector('input[name="jornada"]')?.value || '';
    if (jornadaRaw.includes(':')) {
        const parts = jornadaRaw.split(':');
        step2.jornada = parseFloat((parseInt(parts[0]) + parseInt(parts[1]) / 60).toFixed(2));
    }
    const atividade_vinculos = {};
    document.querySelectorAll('.turma-accordion').forEach((accordion, idx) => {
        const checkboxes = accordion.querySelectorAll('input[type="checkbox"]:checked');
        atividade_vinculos[`turma_${idx + 1}`] = Array.from(checkboxes).map(cb => cb.value);
    });
    const step3 = {
        atividade_vinculos: atividade_vinculos,
        reatribuicao_mode: document.querySelector('input[name="reatribuicao_mode"]:checked')?.value || 'paralelo',
        reatribuicao_template: {},
        paralelo_template: {},
        primaria_template: {}
    };
    const tariffGaps = {};
    document.querySelectorAll('#tariff-gaps-list > div').forEach((div, i) => {
        const key = div.dataset.gapKey || `gap_${i}`;
        const hh = div.querySelector('input[name="manual_hh"]')?.value || '8.0';
        const preco = div.querySelector('input[name="manual_preco"]')?.value || '0.0';
        tariffGaps[key] = { hh_ha: parseFloat(hh), preco_ha: parseFloat(preco), resolved: true };
    });
    const modoComparativo = document.querySelector('input[name="modo_comparativo"]:checked')?.value || 'off';
    const step4 = {
        orcamento_estrito: document.querySelector('input[name="orcamento_estrito"]:checked')?.value === 'true',
        tariff_gaps: Object.entries(tariffGaps).map(([key, val]) => ({ key, ...val })),
        tariff_gap_resolutions: tariffGaps,
        modo_comparativo: modoComparativo,
        substituicoes_comparativo: {},
        multifator: modoComparativo === 'multi-factor',
        external_mecanizado: {}
    };
    const step5 = { confirmed: document.getElementById('confirm-checkbox')?.checked || false };
    return { step1, step2, step3, step4, step5 };
}

function runWizard() {
    const data = collectAllSteps();
    api('/start', {
        method: 'POST',
        body: JSON.stringify(data)
    }).then(res => {
        window.location.href = '/wizard/running/' + res.job_id;
    }).catch(e => {
        console.error('Error starting wizard:', e);
        alert('Erro ao iniciar execução: ' + e.message);
    });
}

    document.addEventListener('DOMContentLoaded', function() {
        initFarmSearch();
        initMethodologyScope();
initTalhaoScope();
initMunicipalityFilter();
initTeamBuilder();
        initJornadaInput();
        initActivityAccordions();
        initOrphanHandling();
        initTariffGaps();
        initComparativoMode();
        initExternalMecanizado();

        // Check if on activity step and farm is selected
        const currentStep1Farm = '{{ state.step1.farm_name if state else "" }}';
        const farmInput = document.querySelector('input[name="farm_name"]');
        if (document.getElementById('activity-linker-container') && farmInput && farmInput.value && currentStep1Farm === farmInput.value) {
            loadActivities();
        }
    });

 // Init on htmx:afterSwap for step transitions
 document.addEventListener('htmx:afterSwap', function(evt) {
     const target = evt.detail.target;
     if (target.id === 'wizard-content') {
         const stepLabel = document.querySelector('.wizard-current-step')?.textContent || '';
         if (stepLabel.includes('Atividades') || stepLabel.includes('3')) {
             initActivityAccordions();
             initOrphanHandling();
             loadActivities();
         } else if (stepLabel.includes('Orçamento') || stepLabel.includes('4')) {
             initTariffGaps();
             initComparativoMode();
             initExternalMecanizado();
         } else if (stepLabel.includes('Equipes') || stepLabel.includes('2')) {
             initTeamBuilder();
             initJornadaInput();
         }
     }
 });

    // Expose helpers globally
    window.wizardHelpers = {
        escapeHtml,
        initFarmSearch,
        initTeamBuilder,
        initActivityAccordions,
        loadActivities,
        runWizard
    };
})();