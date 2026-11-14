
const fs = require("fs");
const path = require("path");

const TAXONOMY_PATH = path.resolve(
    __dirname,
    "../../../configs/taxonomy_mapping_provisional_v1.json"
);

// Parsed taxonomy, keyed by file modification time so edits are picked up
// without re-reading and re-parsing the file on every request.
let cachedTaxonomy = null;
let cachedMtimeMs = null;

const loadTaxonomy = () => {
    if (!fs.existsSync(TAXONOMY_PATH)) {
        throw new Error(
            `Taxonomy configuration not found: ${TAXONOMY_PATH}`
        );
    }

    const { mtimeMs } = fs.statSync(TAXONOMY_PATH);

    if (cachedTaxonomy && cachedMtimeMs === mtimeMs) {
        return cachedTaxonomy;
    }

    let taxonomy;

    try {
        const rawContent = fs.readFileSync(TAXONOMY_PATH, "utf8");
        taxonomy = JSON.parse(rawContent);
    } catch (error) {
        throw new Error(
            `Unable to load taxonomy configuration: ${error.message}`
        );
    }

    if (
        !taxonomy ||
        !Array.isArray(taxonomy.mappings) ||
        !taxonomy.registry_status
    ) {
        throw new Error("Taxonomy configuration has an invalid structure.");
    }

    cachedTaxonomy = taxonomy;
    cachedMtimeMs = mtimeMs;

    return taxonomy;
};

// Return unique target categories from the registry.
// The unknown-source policy is deliberately excluded from assignable categories.
const getCategories = () => {
    const taxonomy = loadTaxonomy();
    const categoryMap = new Map();

    for (const mapping of taxonomy.mappings) {
        const code = mapping.proposed_target_category_code;
        const name = mapping.proposed_target_category;

        if (
            typeof code !== "string" ||
            typeof name !== "string" ||
            !code.trim() ||
            !name.trim()
        ) {
            continue;
        }

        if (!categoryMap.has(code)) {
            categoryMap.set(code, {
                code,
                name,
                mappingStatuses: new Set(),
                sourceLabels: new Set(),
                requiresManualReview: false,
            });
        }

        const category = categoryMap.get(code);

        category.mappingStatuses.add(mapping.mapping_status);

        if (mapping.source_category_title) {
            category.sourceLabels.add(mapping.source_category_title);
        }

        if (mapping.mapping_status === "MANUAL_REVIEW_REQUIRED") {
            category.requiresManualReview = true;
        }
    }

    return Array.from(categoryMap.values())
        .map((category) => ({
            code: category.code,
            name: category.name,

            // Preserve all source mapping review states.
            mappingStatuses: Array.from(category.mappingStatuses),

            sourceLabels: Array.from(category.sourceLabels),

            requiresManualReview: category.requiresManualReview,
        }))
        .sort((a, b) => a.name.localeCompare(b.name));
};

// Find a category using its exact category code.
const getCategoryByCode = (categoryCode) => {
    if (typeof categoryCode !== "string") {
        return null;
    }

    const normalizedCode = categoryCode.trim().toUpperCase();

    return (
        getCategories().find(
            (category) => category.code === normalizedCode
        ) || null
    );
};

// Return registry metadata without treating it as approved.
const getTaxonomyMetadata = () => {
    const taxonomy = loadTaxonomy();

    return {
        registryName: taxonomy.registry_name,
        version: taxonomy.version,
        registryStatus: taxonomy.registry_status,
        purpose: taxonomy.purpose,
        targetProject: taxonomy.target_project,
        sourceDataset: taxonomy.source_dataset,
        totalCategories: getCategories().length,
    };
};

module.exports = {
    loadTaxonomy,
    getCategories,
    getCategoryByCode,
    getTaxonomyMetadata,
};
