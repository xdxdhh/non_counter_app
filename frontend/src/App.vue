<template>
  <div>session id: {{ sessionId }}</div>
  <div class="container">
    <Stepper value="1">
      <StepItem value="1">
        <Step>Input, Platform</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #title>Input, Platform</template>
            <template #subtitle
              >Fill in the Gitlab issue number to automatically downloand the sample file, detect platform and customer
              notes.</template
            >
            <template #content>
              <div class="flex items-center gap-2">
                <span>Gitlab Issue ID (without #): </span>
                <InputText v-model="gitlabIssue" style="width: 200px" />
                <Button label="Fill from issue" @click="() => fillFromGitlab()" severity="info" />
              </div>
              <div v-if="stepNumber >= 2">
                <Card class="!bg-white rounded-xl border border-slate-200 p-2 mt-5">
                  <template #content>
                    <div class="font-bold text-lg">Input Information</div>
                    <div>This section puts together information from customer, Gitlab issue and provided file.</div>
                    <div class="mt-2">
                      <span class="font-bold"
                        >Note (any infofrom the customer, want to take into account for processing):</span
                      >
                      <Textarea v-model="userComment" rows="4" cols="65" />
                    </div>
                    <div>
                      <span class="font-bold">GItlab Issue:</span>
                      <a
                        :href="gitlabIssueUrl"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:underline"
                      >
                        #{{ gitlabIssue }}
                      </a>
                    </div>
                    <div>
                      <span class="font-bold">Downloaded File:</span> {{ selectedFileName }}
                      <span v-if="selectedFileName" class="text-green-600 ml-1">✓</span>
                      <span v-else>-</span>
                    </div>
                  </template>
                </Card>

                <div class="mt-5 ml-2">
                  AI found / did not find similar platform in the Brain. Either use it, or create a new platform.
                </div>

                <div class="flex gap-4">
                  <Card class="!bg-white !border !border-slate-200 !rounded-xl !mt-5 flex-1">
                    <template #content>
                      <div class="font-bold text-lg mb-2">New Platform</div>
                      <div class="flex flex-col gap-2">
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.name" />
                          <label for="on_label">Name</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Full name of the platform'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.short_name" />
                          <label for="on_label">Short Name</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Short name of the platform, can be same as the full name'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.provider" />
                          <label for="on_label">Provider</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Provider of the platform, e.g. EBSCO, ProQuest, etc.'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.url" />
                          <label for="on_label">URL</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'URL of the platform, must be valid URL starting with http...'"
                          />
                        </FloatLabel>
                        <Button
                          label="Create this platform"
                          @click="() => processPlatform(activateCallback, newPlatformInfo)"
                          severity="info"
                          class="self-start"
                          :disabled="
                            !newPlatformInfo.name ||
                            !newPlatformInfo.short_name ||
                            !newPlatformInfo.provider ||
                            !newPlatformInfo.url
                          "
                        />
                      </div>
                    </template>
                  </Card>
                  <Card class="!bg-white !border !border-slate-200 !rounded-xl !mt-5 flex-1">
                    <template #content>
                      <div class="font-bold text-lg mb-2">Existing Platform</div>
                      <a
                        :href="`https://brain.celus.net/admin/knowledgebase/platform/${existingPlatformInfo.pk}/change/`"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:underline"
                      >
                        Platform in Brain
                      </a>
                      <div class="flex flex-col gap-2 mt-2">
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.name" />
                          <label for="on_label">Name</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.short_name" />
                          <label for="on_label">Short Name</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputNumber v-model="existingPlatformInfo.pk" />
                          <label for="on_label">ID</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'ID of the platform in Brain'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.provider" />
                          <label for="on_label">Provider</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.url" />
                          <label for="on_label">URL</label>
                        </FloatLabel>
                        <Button
                          label="Use existing platform"
                          @click="() => processPlatform(activateCallback, existingPlatformInfo)"
                          severity="info"
                          class="self-start"
                          :disabled="
                            !existingPlatformInfo.name ||
                            !existingPlatformInfo.short_name ||
                            !existingPlatformInfo.pk ||
                            !existingPlatformInfo.provider ||
                            !existingPlatformInfo.url
                          "
                        />
                      </div>
                    </template>
                  </Card>
                </div>
              </div>
            </template>
            <template #footer>
              {{ platformError }}
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="2">
        <Step>Metrics,Dimensions,Report Type</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #title>Metrics,Dimensions,Report Type</template>
            <template #content>
              <div class="data-description" v-if="dataDescriptionState == 'done'">
                <div style="padding-top: 10px; padding-bottom: 20px">
                  This is the data information received from the input file. Please modify it if you find any
                  discrepancies or if some metrics or dimensions are unnecessary. This information will be used to
                  generate the parsing rules.
                </div>

                <div class="!bg-white !border !border-slate-200 !rounded-xl p-6">
                  <div class="font-bold text-lg mb-2">Received Data File</div>
                  <div class="flex flex-col gap-2">
                    <div class="flex items-center gap-2">
                      <span>Start month year: </span>
                      <InputText id="begin_month_text" v-model="descriptionData.begin_month_year" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'First full month in the data file'"
                      />
                    </div>
                    <div class="flex items-center gap-2">
                      <span>End month year: </span>
                      <InputText id="end_month_text" v-model="descriptionData.end_month_year" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Last full month in the data file'"
                      />
                    </div>

                    <div class="flex items-center gap-2">
                      <span>English: </span>
                      <Checkbox v-model="descriptionData.english" binary />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Whether the data is in English'"
                      />
                      <span v-if="!descriptionData.english" class="pl-2 ml-2"
                        >Do you want to translate the data?
                        <Button label="Yes" @click="translateData" />
                      </span>
                      <div v-if="translations">Generated translations for metrics: {{ metricsTranslations }}</div>
                      <div v-if="translations">Generated translations for dimensions: {{ dimTranslations }}</div>
                    </div>
                    <div class="flex items-center gap-2">
                      <span>Granularity: </span>
                      <Select
                        id="granularity_select"
                        v-model="descriptionData.granularity"
                        :options="granularityOptions"
                        style="width: 250px"
                      />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Data aggregation - we currently only support daily and monthly data'"
                      />
                    </div>

                    <div class="flex items-center gap-2">
                      <span>Title report:</span>
                      <Checkbox v-model="descriptionData.title_report" binary inputId="title_report_cb" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Does the file include information about titles?'"
                      />
                    </div>

                    <div v-if="descriptionData.title_report" class="flex items-center gap-2">
                      <FloatLabel variant="on">
                        <MultiSelect
                          id="identifiers_multiselect"
                          v-model="descriptionData.title_identifiers"
                          :options="titleIdentifierOptions"
                          style="width: 250px"
                        />
                        <label for="identifiers_multiselect">Title Identifiers</label>
                        <i
                          class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                          v-tooltip="
                            'Which identifiers are used for the titles? Proprietary is for any other identifiers.'
                          "
                        />
                      </FloatLabel>
                    </div>
                  </div>

                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <div class="font-bold text-lg mb-2 mt-4">Metrics</div>
                      Here you can .... map
                      <DataTable
                        :value="metricMappings"
                        dataKey="id"
                        size="small"
                        stripedRows
                        style="width: 100%"
                        :tableStyle="{ tableLayout: 'fixed' }"
                        :emptyMessage="'No metrics yet'"
                      >
                        <Column header="Data metric" style="width: 14rem">
                          <template #body="{ data }">
                            <Select
                              class="cell-select-wrap"
                              v-model="data.dataMetric"
                              :options="availableDataValues"
                              placeholder="Pick data metric/dimension"
                              appendTo="body"
                              scrollHeight="18rem"
                              :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                              filter
                              editable
                              filterPlaceholder="Search data columns/rows..."
                              style="width: 100%"
                            />
                          </template>
                        </Column>
                        <Column header="Brain metric">
                          <template #body="{ data }">
                            <Select
                              class="cell-select-wrap"
                              v-model="data.brainMetric"
                              :options="brainMetricOptions"
                              optionLabel="label"
                              optionValue="value"
                              placeholder="Pick brain metric"
                              appendTo="body"
                              scrollHeight="18rem"
                              :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                              filter
                              filterBy="label"
                              filterPlaceholder="Search brain metrics..."
                              style="width: 100%"
                            />
                          </template>
                        </Column>
                        <Column header="Actions" style="width: 6rem">
                          <template #body="{ data }">
                            <Button icon="pi pi-trash" severity="danger" text @click="() => deleteMetricRow(data.id)" />
                          </template>
                        </Column>
                      </DataTable>
                      <div style="padding-top: 8px">
                        <Button icon="pi pi-plus" label="Add" severity="secondary" @click="addMetricRow" />
                      </div>
                    </FloatLabel>
                  </div>
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <div style="font-weight: 600; padding-bottom: 6px">Dimensions</div>
                      <DataTable
                        :value="dimensionMappings"
                        dataKey="id"
                        size="small"
                        stripedRows
                        style="width: 100%"
                        :tableStyle="{ tableLayout: 'fixed' }"
                        :emptyMessage="'No dimensions yet'"
                      >
                        <Column header="Data dimension" style="width: 14rem">
                          <template #body="{ data }">
                            <Select
                              class="cell-select-wrap"
                              v-model="data.dataDimension"
                              :options="availableDataValues"
                              placeholder="Pick data metric/dimension"
                              appendTo="body"
                              scrollHeight="18rem"
                              :panelStyle="{ width: '20rem', maxWidth: 'calc(100vw - 2rem)' }"
                              filter
                              editable
                              filterPlaceholder="Search data metric/dimension..."
                              style="width: 100%"
                            />
                          </template>
                        </Column>
                        <Column header="Brain dimension">
                          <template #body="{ data }">
                            <Select
                              class="cell-select-wrap"
                              v-model="data.brainDimension"
                              :options="brainDimensionOptions"
                              optionLabel="label"
                              optionValue="value"
                              placeholder="Pick brain dimension"
                              appendTo="body"
                              scrollHeight="18rem"
                              :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                              filter
                              filterBy="label"
                              filterPlaceholder="Search brain dimensions..."
                              style="width: 100%"
                            />
                          </template>
                        </Column>
                        <Column header="Actions" style="width: 6rem">
                          <template #body="{ data }">
                            <Button
                              icon="pi pi-trash"
                              severity="danger"
                              text
                              @click="() => deleteDimensionRow(data.id)"
                            />
                          </template>
                        </Column>
                      </DataTable>
                      <div style="padding-top: 8px">
                        <Button icon="pi pi-plus" label="Add" severity="secondary" @click="addDimensionRow" />
                      </div>
                    </FloatLabel>
                  </div>
                  <div>
                    <Button label="Submit Metrics and Dimensions" @click="() => submitMetricsAndDimensions()" />
                  </div>
                </div>
              </div>
            </template>
            <template #footer>
              <div v-if="dataDescriptionState == 'done'">
                Please make changes if needed. Do you want to use this data description to generate the parsing rules?
                <div>
                  <Button label="Generate Parsing Rules" @click="() => generateParsingRules(activateCallback)" />
                </div>
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="3">
        <Step>Parsing, Output</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #content>
              <div v-if="parsingRulesState == 'loading'">Generating parsing rules, please wait...</div>
              <div v-if="parsingRulesState == 'done'">These are parsing rules generated by the model.</div>
              <div v-if="parsingRulesState == 'failed'">
                Parsing rules generation failed. Please retry from the Data Description step.
              </div>
              <div>
                <Textarea v-model="parsingRules" autoResize rows="10" cols="55" /></div
            ></template>
          </Card>
          <div class="py-6">
            <Button label="Back" severity="secondary" @click="activateCallback('2')" />
          </div>
          <DataTable :value="rows">
            <Column v-for="col in columns" :key="col.field" :field="col.field" size="small" :header="col.header" />
          </DataTable>
        </StepPanel>
      </StepItem>
    </Stepper>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import axios from 'axios'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import FloatLabel from 'primevue/floatlabel'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Checkbox from 'primevue/checkbox'
import Stepper from 'primevue/stepper'
import StepItem from 'primevue/stepitem'
import Step from 'primevue/step'
import StepPanel from 'primevue/steppanel'

import {
  axios_client,
  getState,
  setState,
  callWorker,
  getBrainMetrics,
  getBrainDimensions,
  extractErrorMessage,
} from './api'
import type { BrainMetric, BrainDimension, MetricMapping, DimensionMapping } from './api'

const sessionId = ref<number>(0)
const platformState = ref('') // '', 'loading', 'done'
const dataDescriptionState = ref('') //'', 'loading', 'done'
const parsingRulesState = ref('') //'', 'loading', 'done'

const stepNumber = ref(1)

interface PlatformData {
  name: string
  short_name: string
  provider: string
  url: string
  exists: boolean
  pk: number | null
}

const platformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: false,
  pk: null,
})

const newPlatformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: false,
  pk: null,
})

const existingPlatformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: true,
  pk: 0,
})

const userComment = ref('') //user input - any comment
const platformError = ref('')
const file = ref<File | null>(null)
const selectedFileName = ref('')
const gitlabIssue = ref('')
const gitlabIssueUrl = computed(() => `https://gitlab.com/big-dig-data/celus/-/issues/${gitlabIssue.value}`)

const titleIdentifierOptions: string[] = ['Print_ISSN', 'Online_ISSN', 'ISBN', 'DOI', 'URI', 'Proprietary']
const granularityOptions: string[] = ['daily', 'monthly', 'other']

const parsingRules = ref('') // JSON string of the parsing rules

type ParsedDataColumn = { field: string; header: string }
const columns = ref<ParsedDataColumn[]>([]) // columns of the parsed data (from backend)
const rows = ref<Record<string, any>[]>([]) // rows of the parsed data (array of objects)

const translations = ref(false) //whether to translate the data
const dimTranslations = ref([])
const metricsTranslations = ref([])

interface DataDescriptionData {
  begin_month_year: string
  end_month_year: string
  english: boolean
  title_report: boolean
  granularity: string
  title_identifiers: string[]
  metrics: string[]
  dimensions: string[]
}

const descriptionData = reactive<DataDescriptionData>({
  begin_month_year: '',
  end_month_year: '',
  english: false,
  title_report: false,
  granularity: '',
  title_identifiers: [],
  metrics: [],
  dimensions: [],
})

// Simplified metric and dimension mappings - single source of truth
const metricMappings = ref<MetricMapping[]>([])
const dimensionMappings = ref<DimensionMapping[]>([])

// Auto-incrementing ID counter for table rows (frontend only)
let nextRowId = 0

// Available options for dropdown (union of metrics and dimensions from file)
const availableDataValues = computed(() => {
  return [...new Set([...descriptionData.metrics, ...descriptionData.dimensions])]
})

const brainMetrics = ref<BrainMetric[]>([])
const brainMetricOptions = computed(() =>
  (brainMetrics.value || []).map((m) => ({
    label: m.toDisplay(),
    value: m.short_name,
  })),
)

const brainDimensions = ref<BrainDimension[]>([])
const brainDimensionOptions = computed(() =>
  (brainDimensions.value || []).map((d) => ({
    label: d.toDisplay(),
    value: d.short_name,
  })),
)

// JSON.stringify replacer can't reliably remove nulls inside arrays (they become `null`),
// so we deep-clean the object first, then stringify the cleaned object.
const deepOmitNulls = (value: any): any => {
  if (value === null) return undefined
  if (Array.isArray(value)) {
    const cleaned = value.map((v) => deepOmitNulls(v)).filter((v) => v !== undefined)
    return cleaned.length === 0 ? undefined : cleaned
  }
  if (typeof value === 'object' && value) {
    const out: Record<string, any> = {}
    for (const [k, v] of Object.entries(value)) {
      const cleaned = deepOmitNulls(v)
      if (cleaned !== undefined) out[k] = cleaned
    }
    // if object became empty, omit it too
    return Object.keys(out).length === 0 ? undefined : out
  }
  return value
}

// Simple add/delete functions for metric mappings
const addMetricRow = () => {
  metricMappings.value.push({
    id: nextRowId++,
    dataMetric: '',
    brainMetric: '',
  })
}

const deleteMetricRow = (id: number) => {
  metricMappings.value = metricMappings.value.filter((m) => m.id !== id)
}

// Simple add/delete functions for dimension mappings
const addDimensionRow = () => {
  dimensionMappings.value.push({
    id: nextRowId++,
    dataDimension: '',
    brainDimension: '',
  })
}

const deleteDimensionRow = (id: number) => {
  dimensionMappings.value = dimensionMappings.value.filter((d) => d.id !== id)
}

const generateParsingRules = async (activateCallback: (step: string) => void) => {
  parsingRulesState.value = 'loading'
  parsingRules.value = ''
  activateCallback('3')
  console.log('Generating parsing rules for platform:', platformInfo.name)

  // Extract just the data metric/dimension names as simple string arrays for backend
  const dataDescriptionForBackend = {
    ...descriptionData,
    metrics: metricMappings.value.map((m) => m.dataMetric),
    dimensions: dimensionMappings.value.map((d) => d.dataDimension),
  }

  await setState(sessionId.value, 'data_description_data', dataDescriptionForBackend)
  await callWorker(sessionId.value, 'parsing_rules_worker')
  const newParsingRules = await getState(sessionId.value, 'parser_definition_data')
  if (newParsingRules == null) {
    parsingRulesState.value = 'failed'
    return
  }
  parsingRules.value = JSON.stringify(deepOmitNulls(newParsingRules), null, 3)
  parsingRulesState.value = 'done'
  const parsedData = await getState(sessionId.value, 'parsed_data')
  columns.value = parsedData.columns
  rows.value = parsedData.rows
  console.log('Parsed data:', parsedData)
}

const onFileSelect = (event: { files: File[] }) => {
  console.log('File selected:', event.files[0])
  file.value = event.files[0] // Store the selected file
  selectedFileName.value = event.files[0]?.name || ''
}

const processPlatform = async (activateCallback: (step: string) => void, platformData: PlatformData) => {
  platformError.value = ''
  dataDescriptionState.value = 'loading'
  // go to second step in stepper
  console.log('Processing platform:', platformData.name)

  // update user comment - TODO (+ do not forget gitlab issue)
  //await setState(sessionId.value, 'user_info_data', {
  //  user_comment: userComment.value,
  //})

  // update platform data
  console.log('Updating platform data:', platformData)
  try {
    await setState(sessionId.value, 'platform_data', { ...platformData })
    //dunno about the file
    await axios_client.get(`submit_platform/${sessionId.value}`) //submit platform to gitlab
    activateCallback('2')
  } catch (error) {
    console.error('Error submitting platform:', error)
    platformError.value = extractErrorMessage(error)
  }

  await generateDescription()
}

const submitMetricsAndDimensions = async () => {
  // Backend expects snake_case keys and nested BrainMetric/BrainDimension objects (or null).
  // Our table stores brainMetric/brainDimension as selected short_name strings, so we look up full objects.
  const brainMetricByShortName = new Map(brainMetrics.value.map((m) => [m.short_name, m]))
  const brainDimensionByShortName = new Map(brainDimensions.value.map((d) => [d.short_name, d]))

  const payload = {
    metrics: metricMappings.value.map((m) => {
      const selected = m.brainMetric ? brainMetricByShortName.get(m.brainMetric) : undefined
      return {
        data_metric: m.dataMetric,
        brain_metric: selected ? { id: selected.id, short_name: selected.short_name, aliases: selected.aliases } : null,
      }
    }),
    dimensions: dimensionMappings.value.map((d) => {
      const selected = d.brainDimension ? brainDimensionByShortName.get(d.brainDimension) : undefined
      return {
        data_dimension: d.dataDimension,
        brain_dimension: selected
          ? { id: selected.id, short_name: selected.short_name, aliases: selected.aliases }
          : null,
      }
    }),
  }

  await setState(sessionId.value, 'metrics_dimensions_data', payload)
  await axios_client.post(`submit_metrics_dimensions/${sessionId.value}`)
  const newMetricsDimensions = await getState(sessionId.value, 'metrics_dimensions_data')
  console.log('Metrics and dimensions:', newMetricsDimensions)
}

const fillFromGitlab = async () => {
  if (!gitlabIssue.value) {
    console.error('No GitLab issue number provided')
    return
  }

  platformState.value = 'loading'
  console.log('Filling platform info from GitLab issue:', gitlabIssue.value)

  // Update user_info_data with both comment and GitLab issue number
  await setState(sessionId.value, 'user_info_data', {
    user_comment: userComment.value,
    gitlab_issue: Number(gitlabIssue.value),
  })

  // Call Gitlab worker to fetch platform info from the issue
  await callWorker(sessionId.value, 'gitlab_worker')

  // Read platform_data returned by the worker and use it as in processPlatform
  const newPlatformData = await getState(sessionId.value, 'platform_data')
  console.log('Platform data from GitLab:', newPlatformData)
  Object.assign(platformInfo, newPlatformData)
  platformState.value = 'done'

  if (platformInfo.exists) {
    console.log('Using existing platform:', existingPlatformInfo)
    Object.assign(existingPlatformInfo, platformInfo)
  } else {
    console.log('Creating new platform:', newPlatformInfo)
    Object.assign(newPlatformInfo, platformInfo)
  }

  // Also check if file_data is available (it might have been set by the worker)
  const fileData = await getState(sessionId.value, 'file_data')
  if (fileData && fileData.file_name) {
    console.log('File data from GitLab:', fileData)
    // IMPORTANT: don't create a dummy File and upload it, it would overwrite the real file
    // downloaded by the backend GitLab worker. We only use this for display.
    selectedFileName.value = fileData.file_name
    file.value = null
  }

  stepNumber.value = 2
}

const sendFile = async () => {
  if (!file.value) {
    return
  }

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const response = await axios_client.post(`upload_file/${sessionId.value}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  } catch (error) {
    console.error('Error uploading file:', error)
  }
}

const generateDescription = async () => {
  dataDescriptionState.value = 'loading'
  await callWorker(sessionId.value, 'data_description_worker')
  const newDataDescription = await getState(sessionId.value, 'data_description_data')
  Object.assign(descriptionData, newDataDescription)

  // Populate metric mappings from backend data (generate simple IDs on frontend)
  metricMappings.value = (newDataDescription.metrics || []).map((metricName: string) => ({
    id: nextRowId++,
    dataMetric: metricName,
    brainMetric: '',
  }))

  // Populate dimension mappings from backend data (generate simple IDs on frontend)
  dimensionMappings.value = (newDataDescription.dimensions || []).map((dimensionName: string) => ({
    id: nextRowId++,
    dataDimension: dimensionName,
    brainDimension: '',
  }))

  dataDescriptionState.value = 'done'
}

const translateData = async () => {
  translations.value = true
  await callWorker(sessionId.value, 'translation_worker')
  const newTranslations = await getState(sessionId.value, 'translation_data')
  metricsTranslations.value = newTranslations.metrics_translations
  dimTranslations.value = newTranslations.dimensions_translations
}

onMounted(async () => {
  try {
    const response = await axios.post('http://127.0.0.1:8000/start_session')
    sessionId.value = response.data.session_id
    const metrics = await getBrainMetrics()
    brainMetrics.value = metrics || []
    const dims = await getBrainDimensions()
    brainDimensions.value = dims || []
  } catch (error) {
    console.error('Failed to start session:', error)
  }
})
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}

/* Prevent long Select labels from expanding the table; wrap to multiple lines instead */
:deep(.p-datatable td) {
  min-width: 0;
}

:deep(.cell-select-wrap) {
  min-width: 0;
  max-width: 100%;
}

:deep(.cell-select-wrap .p-select-label) {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.2;
}
.input-box {
  width: 300px;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.send-button {
  padding: 8px 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.send-button:hover {
  background-color: #0056b3;
}

.p-multiselect {
  min-width: 17rem;
  max-width: 400px;
}

.input-card-content {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.input-card-left,
.input-card-right {
  flex: 1;
}

.input-card-divider {
  width: 1px;
  align-self: stretch;
  background-color: #e0e0e0;
}

.helper-text {
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
