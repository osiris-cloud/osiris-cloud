window.addEventListener('load', () => {
    const $runningN = $("#running-n");
    const $pendingN = $("#pending-n");
    const $desiredN = $("#desired-n");
    const $reqUsage = $('#req-usage');
    const $respUsage = $('#resp-usage');
    const $requestCount = $('#request-count');
    const $events = $("#events");
    const $noEventsMessage = $('#no-events-message');

    const isDarkMode = localStorage.getItem('theme') === 'dark';

    window.updateStatChart = function updateStatChart(running, pending, desired) {
        $runningN.text(running);
        $pendingN.text(pending);
        $desiredN.text(desired);

        const width = 200;
        const height = 200;
        const margin = 20;
        const radius = Math.min(width, height) / 2 - margin;

        const isEmpty = running === 0 && pending === 0;
        const data = isEmpty ?
            [{label: "empty", value: 1, color: "rgba(156, 163, 175, 0.3)"}] :
            [
                {label: "running", value: running, color: "#30c264"},
                {label: "pending", value: pending, color: "#e7af04"}
            ];

        const arc = d3.arc().innerRadius(radius * 0.6).outerRadius(radius);

        const svg = d3.select("#stat-chart")
            .selectAll("svg")
            .data([null])
            .join("svg")
            .attr("width", width)
            .attr("height", height);

        const g = svg.selectAll("g")
            .data([null])
            .join("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

        const pie = d3.pie().value(d => d.value).sort(null);

        const paths = g.selectAll("path")
            .data(pie(data));

        paths.enter()
            .append("path")
            .merge(paths)
            .transition()
            .duration(750)
            .attrTween("d", function (d) {
                const interpolate = d3.interpolate(this._current || d, d);
                this._current = interpolate(0);
                return function (t) {
                    return arc(interpolate(t));
                };
            })
            .attr("fill", d => d.data.color);

        paths.exit().remove();

        const availability = isEmpty ? 0 : (running / desired) * 100;

        g.selectAll(".center-text")
            .data([null])
            .join("text")
            .attr("class", "center-text")
            .attr("dy", "-0.1em")
            .style("fill", isDarkMode ? 'rgba(255,255,255,0.82)' : '#1a1a1a')
            .text(`${Math.round(availability)}%`);

        g.selectAll(".center-label")
            .data([null])
            .join("text")
            .attr("class", "center-label")
            .attr("dy", "1.2em")
            .style("fill", isDarkMode ? '#9ca3af' : '#6b7280')
            .text("Availability");
    }

    function getEventType(message) {
        return message.toLowerCase().includes('up') ? 'scale-up' : 'scale-down';
    }

    function createEventElement(event) {
        const eventType = getEventType(event.message);
        const template = document.getElementById(`${eventType}-template`);
        const $clone = $(template.content.cloneNode(true));

        $clone.find('.event-message').text(event.message);
        $clone.find('.event-time')
            .text(normalizeTime(event.time, true))
            .attr('data-started_at', event.time);

        return $clone;
    }

    window.updateEvents = function updateEvents(events) {
        $events.find('.events-container').remove();

        if (events.length === 0) {
            $noEventsMessage.show();
            return;
        }

        $noEventsMessage.hide();

        const $eventsContainer = $('<div>')
            .addClass('events-container space-y-4 overflow-y-auto')
            .css('max-height', 'calc(100% - 2rem)');

        $.each(events, function (index, event) {
            const $event = createEventElement(event);
            $eventsContainer.append($event);
        });

        $events.append($eventsContainer);
    }

    function formatMemory(memoryMB) {
        return memoryMB >= 1000
            ? {'value': (memoryMB / 1000).toFixed(2), 'unit': 'GiB'}
            : {'value': memoryMB.toFixed(1), 'unit': 'MiB'};
    }

    function formatNumber(value) {
        return parseFloat(value).toString();
    }

    function createGauge(elementId, value, maxValue) {
        const opts = {
            colorScale: value === 0 ?
                () => "rgba(156, 163, 175, 0.3)" :  // gray for zero/empty state
                d3.scaleThreshold()
                    .domain([0.8 * maxValue, 0.9 * maxValue])
                    .range(["#30c264", "#e7af04", "#ef4444"]),
            startAngle: -140 * (Math.PI / 180),
            endAngle: 140 * (Math.PI / 180),
            animationDuration: 750
        };

        const width = 128;
        const height = 128;
        const radius = 54;
        const strokeWidth = 8;
        const innerRadius = radius - strokeWidth + 4;
        const center = {x: width / 2, y: height / 2};

        const angleScale = d3.scaleLinear()
            .domain([0, maxValue])
            .range([opts.startAngle, opts.endAngle]);

        const arc = d3.arc()
            .innerRadius(innerRadius)
            .outerRadius(radius)
            .startAngle(opts.startAngle)
            .cornerRadius(7);

        let svg = d3.select(`#${elementId} svg`);
        if (svg.empty()) {
            // Initial setup for new gauge
            svg = d3.select(`#${elementId}`)
                .append("svg")
                .attr("width", width)
                .attr("height", height)
                .append("g")
                .attr("transform", `translate(${center.x},${center.y})`);

            // Background arc
            svg.append("path")
                .datum({endAngle: opts.endAngle})
                .attr("d", arc)
                .attr("fill", "none")
                .attr("stroke", "rgb(55, 65, 81)")
                .attr("stroke-width", strokeWidth)
                .attr("stroke-linecap", "round");

            // Progress arc
            svg.append("path")
                .attr("class", "progress-arc")
                .attr("fill", "none")
                .attr("stroke-width", strokeWidth)
                .attr("stroke-linecap", "round")
                .datum({endAngle: opts.startAngle}) // Initialize with startAngle
                .attr("d", arc); // Set initial path

            // Text container
            d3.select(`#${elementId}`).append("div")
                .attr("class", "absolute inset-0 flex flex-col items-center justify-center text-center")
                .html(`
                <span id="${elementId}-value" class="text-lg font-semibold text-gray-800 dark:text-gray-200">0</span>
                <span id="${elementId}-unit" class="text-xs text-gray-600 dark:text-gray-400"></span>
            `);
        }

        // For zero value, show full arc in gray
        const endAngle = value === 0 ? opts.endAngle : angleScale(Math.max(0.001, value));
        const progressArc = svg.select(".progress-arc");

        // Get the current end angle
        const currentEndAngle = progressArc.datum().endAngle;

        // Update the datum and animate
        progressArc
            .datum({endAngle: endAngle})
            .attr("stroke", opts.colorScale(value))
            .transition()
            .duration(opts.animationDuration)
            .attrTween("d", function () {
                const interpolate = d3.interpolate(currentEndAngle, endAngle);
                return function (t) {
                    return arc({
                        startAngle: opts.startAngle,
                        endAngle: interpolate(t)
                    });
                };
            });

        // Update text values
        if (elementId === "memory-gauge") {
            const formatted = formatMemory(value);
            d3.select(`#${elementId}-value`).text(formatted.value);
            d3.select(`#${elementId}-unit`).text(formatted.unit);
        } else {
            const formattedCpuValue = formatNumber(value);
            d3.select(`#${elementId}-value`).text(formattedCpuValue);
            d3.select(`#${elementId}-unit`).text("cores");
        }
    }

    window.updateUsageGauges = function updateUsageGauges({cpu, memory}) {
        createGauge("cpu-gauge", cpu.current, cpu.limit);
        createGauge("memory-gauge", memory.current, memory.limit);
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
    }

    window.updateNetworkStats = function updateNetworkStats(req_bytes, resp_bytes, request_count) {
        $reqUsage.text(formatBytes(req_bytes));
        $respUsage.text(formatBytes(resp_bytes));
        $requestCount.text(request_count);
    };

    updateStatChart(0, 0, 0);
    updateUsageGauges({cpu: {current: 0, limit: 0}, memory: {current: 0, limit: 0}});

});
