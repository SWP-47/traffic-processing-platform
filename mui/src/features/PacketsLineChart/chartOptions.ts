import style from './PacketsLineChart.module.css';
import { colors } from '@/styles/theme';
import type { EChartsOption } from 'echarts';
import type { OptionDataValue } from 'echarts/types/src/util/types.js';

const chartOptions: EChartsOption = {
    // Margins
    grid: { top: 15, right: 15, left: 15, bottom: 30 },

    // Background
    backgroundColor: "transparent",

    // X Axis
    xAxis: {
        type: "time",
        minInterval: 1000,

        offset: 20,
        animationDuration: 0,
        animationEasingUpdate: "linear",
        animationDurationUpdate: 1000,
        
        axisLabel: {
            color: colors.text,
            fontWeight: "lighter",
            fontFamily: "Manrope",
            fontSize: 16,
            hideOverlap: true,
            padding: [0, 5],
        },
    },

    // Y Axis
    yAxis: {
        splitLine: { lineStyle: { color: colors.surfaceHover } },
        offset: 10,

        axisLabel: {
            color: colors.text,
            fontWeight: "lighter",
            fontFamily: "Manrope",
            fontSize: 16,
        },
    },

    // Zoom
    dataZoom: [
        {
            id: "dataZoomX",
            type: "inside",
            xAxisIndex: [0],
            filterMode: "none",
            minValueSpan: 2000
        },
    ],

    // Tool-tip
    tooltip: {
        trigger: 'axis',
        className: style.tooltipWrapper,

        formatter: function (params) {
            if (!params) return '';
            if (!Array.isArray(params)) return '';
            if (!params[0]) return '';
            if (!Array.isArray(params[0].value)) return '';

            // Timestamp / Value / ChannelActivity / WindowSize
            const timestamp       = params[0].value[0]!;
            const channelIsActive = params[0].value[2]!;
            const windowSize      = params[0].value[3]!;

            const time = new Date(timestamp);
            const timeLabel = time.toLocaleString();

            return `
                <div class="${style.tooltip}">
                    <p class="${style.date}">${timeLabel}</p>
                    <p class="${style.window}">${windowSize}</p>
                    <div class="${style.props}">
                        <div class="${style.prop}">
                        <span class="${style.title}">Status:</span>
                        <span>${channelIsActive ? "active" : "inactive"}</span>
                        </div>
                        ${
                            params.map(param => (`
                                <div class="${style.prop}">
                                    <span class="${style.title}" data-name="${param.seriesName}">${param.seriesName}:</span>
                                    <span>${(param.value as OptionDataValue[])[1]} pkt/s</span>
                                </div>
                            `)).join("\n")
                        }
                    </div>
                    <p class="${style.details}">Click for details</p>
                </div>
            `;
        }
    },

    // Legend
    legend: {
        show: false,
        selected: {
            Received: true,
            Sent: true
        },
    },
    
    // Series
    series: [
        {
            name: 'Received',
            type: 'line',

            showSymbol: false,
            symbol: 'circle',
            smooth: 0.2,
            emphasis: { disabled: true },
            itemStyle: { color: colors.primary, },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0,
                    x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: colors.primary },
                        { offset: 1, color: colors.surface }
                    ],
                },
                opacity: 0.1
            },
            animationEasingUpdate: "linear",
            animationDurationUpdate: 1000,

            data: []
        },

        {
            name: 'Sent',
            type: 'line',

            showSymbol: false,
            symbol: 'circle',
            smooth: 0.2,
            emphasis: { disabled: true },
            itemStyle: { color: colors.accent },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0,
                    x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: colors.accent },
                        { offset: 1, color: colors.surface }
                    ],
                },
                opacity: 0.1
            },
            animationEasingUpdate: "linear",
            animationDurationUpdate: 1000,

            data: []
        }
    ]
};

export default chartOptions;