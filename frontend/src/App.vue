<template>
  <div>session id: {{ sessionId }}</div>
  <div class="container">
    <Stepper value="1">
      <StepItem value="1">
        <Step>Input Information</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #title>Input Information</template>
            <template #subtitle
              >Fill in the information from the customer - platform name, the received file and any
              comments you want to provide.</template
            >
            <template #content>
              <div class="input-card-content">
                <div class="input-card-left">
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <InputText id="on_label" v-model="platformInfo.name" style="width: 300px" />
                      <label for="on_label">Platform Name</label>
                    </FloatLabel>
                  </div>
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <Textarea
                        id="over_label"
                        v-model="platformInfo.provider"
                        rows="1"
                        cols="30"
                        style="resize: none"
                      />
                      <label for="on_label">Provider</label>
                    </FloatLabel>
                  </div>
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <Textarea
                        id="over_label"
                        v-model="userComment"
                        rows="5"
                        cols="30"
                        style="resize: none"
                      />
                      <label for="on_label">User Comments</label>
                    </FloatLabel>
                  </div>
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <Textarea
                        id="over_label"
                        v-model="platformInfo.url"
                        rows="1"
                        cols="30"
                        style="resize: none"
                      />
                      <label for="on_label">Platform URL</label>
                    </FloatLabel>
                  </div>
                  <FileUpload
                    ref="fileupload"
                    mode="basic"
                    name="file"
                    :maxFileSize="1000000"
                    @select="onFileSelect"
                    chooseLabel="CSV/Excel File"
                    accept="text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    style="justify-content: left; display: block"
                  />
                  <div v-if="file" style="margin-top: 5px; font-size: 0.9rem; color: #666">
                    Selected file: {{ selectedFileName }}
                  </div>
                </div>

                <div class="input-card-divider" />

                <div class="input-card-right">
                  <div style="font-weight: 600; padding-bottom: 10px">From GitLab</div>
                  <div style="padding-bottom: 10px">
                    <FloatLabel variant="on">
                      <InputText id="gitlab_issue" v-model="gitlabIssue" style="width: 200px" />
                      <label for="gitlab_issue">Issue number</label>
                    </FloatLabel>
                  </div>
                  <small class="helper-text">
                    Paste the GitLab issue number (without #) to autofill the information from this
                    issue.
                  </small>
                  <div style="padding-top: 8px">
                    <Button
                      label="Fill from issue"
                      @click="() => fillFromGitlab()"
                      severity="primary"
                    />
                  </div>
                </div>
              </div>
            </template>
            <template #footer>
              <div style="padding-top: 30px">
                <Button label="Process Platform" @click="() => processPlatform(activateCallback)" />
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="2">
        <Step>Data Description</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #content>
              <div v-if="dataDescriptionState == 'loading'">
                Generating Data Description, please wait...
              </div>
              <div class="data-description" v-if="dataDescriptionState == 'done'">
                <div style="font-weight: bold">Generated Data Description</div>
                <div style="padding-top: 10px; padding-bottom: 20px">
                  This is the data information received from the input file. Please modify it if you
                  find any discrepancies or if some metrics or dimensions are unnecessary. This
                  information will be used to generate the parsing rules.
                </div>

                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <InputText id="begin_month_text" v-model="descriptionData.begin_month_year" />
                    <label for="begin_month_text">Start Month Year</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <InputText id="end_month_text" v-model="descriptionData.end_month_year" />
                    <label for="end_month_text">End Month Year</label>
                  </FloatLabel>
                </div>

                <div class="flex items-center gap-2" style="padding-bottom: 10px">
                  <span>English: </span>
                  <ToggleButton
                    v-model="descriptionData.english"
                    onLabel="Yes"
                    offLabel="No"
                    onIcon="pi pi-lock"
                    offIcon="pi pi-lock-open"
                    size="small"
                    style="width: 100px"
                  />
                  <span v-if="!descriptionData.english" class="pl-2 ml-2"
                    >Do you want to translate the data?
                    <Button label="Yes" @click="translateData" />
                  </span>
                  <div v-if="translations">
                    Generated translations for metrics: {{ metricsTranslations }}
                  </div>
                  <div v-if="translations">
                    Generated translations for dimensions: {{ dimTranslations }}
                  </div>
                </div>

                <div class="flex items-center gap-2" style="padding-bottom: 10px">
                  <span>Title report: </span>
                  <ToggleButton
                    v-model="descriptionData.title_report"
                    onLabel="Yes"
                    offLabel="No"
                    onIcon="pi pi-lock"
                    offIcon="pi pi-lock-open"
                    size="small"
                    style="width: 100px"
                  />
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <MultiSelect
                      id="identifiers_multiselect"
                      v-model="descriptionData.title_identifiers"
                      :options="titleIdentifierOptions"
                      style="width: 250px"
                    />
                    <label for="identifiers_multiselect">Title Identifiers</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <Select
                      id="granularity_select"
                      v-model="descriptionData.granularity"
                      :options="granularityOptions"
                      style="width: 250px"
                    />
                    <label for="granularity_select">Granularity</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <div style="font-weight: 600; padding-bottom: 6px">Metrics</div>
                    <DataTable
                      :value="metricMappings"
                      dataKey="id"
                      size="small"
                      stripedRows
                      style="width: 100%"
                      :emptyMessage="'No metrics yet'"
                    >
                      <Column header="Data metric">
                        <template #body="{ data }">
                          <Select
                            v-model="data.dataMetric"
                            :options="availableDataValues"
                            placeholder="Pick data metric/dimension"
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            editable
                            filterPlaceholder="Search data metric/dimension..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="Brain metric">
                        <template #body="{ data }">
                          <Select
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
                          <Button
                            icon="pi pi-trash"
                            severity="danger"
                            text
                            @click="() => deleteMetricRow(data.id)"
                          />
                        </template>
                      </Column>
                    </DataTable>
                    <div style="padding-top: 8px">
                      <Button
                        icon="pi pi-plus"
                        label="Add"
                        severity="secondary"
                        @click="addMetricRow"
                      />
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
                      :emptyMessage="'No dimensions yet'"
                    >
                      <Column header="Data dimension">
                        <template #body="{ data }">
                          <Select
                            v-model="data.dataDimension"
                            :options="availableDataValues"
                            placeholder="Pick data metric/dimension"
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
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
                      <Button
                        icon="pi pi-plus"
                        label="Add"
                        severity="secondary"
                        @click="addDimensionRow"
                      />
                    </div>
                  </FloatLabel>
                </div>
              </div>
            </template>
            <template #footer>
              <div v-if="dataDescriptionState == 'done'">
                Please make changes if needed. Do you want to use this data description to generate
                the parsing rules?
                <div>
                  <Button
                    label="Generate Parsing Rules"
                    @click="() => generateParsingRules(activateCallback)"
                  />
                </div>
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="3">
        <Step>Parsing Rules</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 50rem; overflow: hidden">
            <template #content>
              <div v-if="parsingRulesState == 'loading'">
                Generating parsing rules, please wait...
              </div>
              <div v-if="parsingRulesState == 'done'">
                These are parsing rules generated by the model.
              </div>
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
            <Column
              v-for="col in columns"
              :key="col"
              :field="col"
              size="small"
              :header="col"
            />
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
import FloatLabel from 'primevue/floatlabel'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import ToggleButton from 'primevue/togglebutton'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import Stepper from 'primevue/stepper'
import StepItem from 'primevue/stepitem'
import Step from 'primevue/step'
import StepPanel from 'primevue/steppanel'

import { axios_client, getState, setState, callWorker, getBrainMetrics, getBrainDimensions } from './api'
import type { BrainMetric, BrainDimension, MetricMapping, DimensionMapping } from './api'

const sessionId = ref<number>(0)
const platformState = ref('') // '', 'loading', 'done'
const dataDescriptionState = ref('') //'', 'loading', 'done'
const parsingRulesState = ref('') //'', 'loading', 'done'

const platformInfo = reactive({
  name: '',
  provider: '',
  url: '',
})

const userComment = ref('') //user input - any comment
const file = ref<File | null>(null)
const selectedFileName = ref('')
const gitlabIssue = ref('')

const titleIdentifierOptions: string[] = [
  'Print_ISSN',
  'Online_ISSN',
  'ISBN',
  'DOI',
  'URI',
  'Proprietary',
]
const granularityOptions: string[] = ['daily', 'monthly', 'other']


const parsingRules = ref('') // JSON string of the parsing rules

const columns = ref<string[]>([]) // columns of the parsed data
const rows = ref<string[][]>([]) // rows of the parsed data

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

const processPlatform = async (activateCallback: (step: string) => void) => {
  dataDescriptionState.value = 'loading'
  activateCallback('2') // go to second step in stepper
  console.log('Processing platform:', platformInfo.name)

  // update user comment
  await setState(sessionId.value, 'user_info_data', {
    user_comment: userComment.value,
  })

  // update platform data
  await setState(sessionId.value, 'platform_data', {
    platform_name: platformInfo.name,
    provider: platformInfo.provider,
    url: platformInfo.url,
  })
  //dunno about the file

  await callWorker(sessionId.value, 'platform_worker')

  const newPlatformData = await getState(sessionId.value, 'platform_data')
  if (newPlatformData) {
    console.log('New platform data:', newPlatformData)
    platformInfo.name = newPlatformData.platform_name
    platformInfo.provider = newPlatformData.provider || ''
    platformInfo.url = newPlatformData.url || ''
    platformState.value = 'done'
  }

  if (file.value) {
    await sendFile()
  }
  await generateDescription()
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
  if (newPlatformData) {
    console.log('Platform data from GitLab:', newPlatformData)
    platformInfo.name = newPlatformData.platform_name
    platformInfo.provider = newPlatformData.provider || ''
    platformInfo.url = newPlatformData.url || ''
    platformState.value = 'done'
  } else {
    console.error('No platform data returned from gitlab_worker')
    platformState.value = ''
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
